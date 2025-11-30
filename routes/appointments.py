from flask import Blueprint, request, jsonify
from app import db
from models.appointment_model import Appointment, AppointmentProcedure
from models.procedure_model import Procedure
from models.patient_model import Patient
from models.user_model import User
from utils.jwt_util import auth_required
from utils.pagination import paginate_query
from datetime import datetime

appointments_bp = Blueprint('appointments_bp', __name__)

# Função auxiliar para verificar se a string não está vazia (após strip).
# Reutilizada de outros arquivos para consistência.
def is_valid_string(value):
    """Retorna True se o valor for uma string não vazia (após strip), False caso contrário."""
    return isinstance(value, str) and bool(value.strip())

def calc_valor_total(proc_objs, tipo):
    total = 0.0
    for p in proc_objs:
        if tipo == 'plano':
            # Assume que a propriedade de valor do procedimento é acessível
            total += p.valor_plano 
        else:
            total += p.valor_particular
    return total

@appointments_bp.route('/', methods=['POST'])
@auth_required
def create_appointment():
    data = request.get_json() or {}
    
    # Campos que precisam estar presentes, mas que serão validados individualmente
    required_keys = ['data_hora','paciente_id','procedimentos','tipo']
    
    # Validação básica de presença
    for f in required_keys:
        if data.get(f) is None:
            return jsonify({'erro':f'Campo {f} obrigatório'}), 400
            
    # Validação de tipo (string não vazia)
    tipo = data['tipo']
    if not is_valid_string(tipo) or tipo not in ['plano','particular']:
        return jsonify({'erro':'tipo deve ser "plano" ou "particular" e não pode ser vazio'}), 400
    
    # parse date
    try:
        data_hora = datetime.fromisoformat(data['data_hora'])
    except Exception:
        return jsonify({'erro':'data_hora formato ISO (YYYY-MM-DDTHH:MM:SS) esperado'}), 400
        
    # Validação do paciente
    paciente = Patient.query.get(data['paciente_id'])
    if not paciente:
        return jsonify({'erro':'Paciente não encontrado'}), 404
        
    # Validação de procedimentos
    proc_ids = data['procedimentos']
    if not isinstance(proc_ids, list) or len(proc_ids)==0:
        return jsonify({'erro':'Deve existir pelo menos um procedimento associado'}), 400
        
    proc_objs = []
    for pid in proc_ids:
        # Garante que o ID do procedimento seja um número inteiro (Flask/JSON podem retornar strings)
        try:
            pid = int(pid)
        except (ValueError, TypeError):
            return jsonify({'erro':f'ID de procedimento inválido: {pid}'}), 400
            
        p = Procedure.query.get(pid)
        if not p:
            return jsonify({'erro':f'Procedimento id {pid} não encontrado'}), 404
        proc_objs.append(p)

    # Validação de numero_carteira para tipo plano
    if tipo == 'plano':
        numero_carteira = data.get('numero_carteira')
        if not is_valid_string(numero_carteira):
             return jsonify({'erro':'numero_carteira obrigatório e não pode ser vazio para tipo plano'}), 400
        numero_carteira_cleaned = numero_carteira.strip()
    else:
        numero_carteira_cleaned = None

    # create appointment
    usuario_id = request.user.get('id')
    valor_total = calc_valor_total(proc_objs, tipo)
    
    ap = Appointment(
        data_hora=data_hora,
        tipo=tipo.strip(),
        numero_carteira=numero_carteira_cleaned,
        valor_total=valor_total,
        usuario_id=usuario_id,
        paciente_id=paciente.id
    )
    
    db.session.add(ap)
    db.session.flush()  # get id
    
    for p in proc_objs:
        ap_proc = AppointmentProcedure(atendimento_id=ap.id, procedimento_id=p.id)
        db.session.add(ap_proc)
        
    db.session.commit()
    return jsonify(ap.to_dict()), 201

@appointments_bp.route('/<int:ap_id>', methods=['GET'])
@auth_required
def get_appointment(ap_id):
    ap = Appointment.query.get_or_404(ap_id)
    return jsonify(ap.to_dict()), 200

@appointments_bp.route('/', methods=['GET'])
@auth_required
def list_appointments():
    query = Appointment.query.order_by(Appointment.id)
    return jsonify(paginate_query(query, lambda a: a.to_dict())), 200

@appointments_bp.route('/<int:ap_id>', methods=['PUT'])
@auth_required
def update_appointment(ap_id):
    ap = Appointment.query.get_or_404(ap_id)
    
    # only creator or admin can edit
    if request.user.get('tipo') != 'admin' and request.user.get('id') != ap.usuario_id:
        return jsonify({'erro':'Apenas criador ou admin pode editar atendimento'}), 403
        
    data = request.get_json() or {}
    
    # Variável para rastrear se os procedimentos foram alterados, o que afeta o valor total
    procedimentos_changed = False 
    
    # Atualiza data_hora
    if data.get('data_hora'):
        # Validação de string não vazia (embora data_hora deva ser string)
        if not is_valid_string(data['data_hora']):
            return jsonify({'erro':'data_hora não pode ser vazio'}), 400
        try:
            ap.data_hora = datetime.fromisoformat(data['data_hora'].strip())
        except:
            return jsonify({'erro':'data_hora formato ISO (YYYY-MM-DDTHH:MM:SS) esperado'}), 400
            
    # Atualiza paciente
    if data.get('paciente_id'):
        p = Patient.query.get(data['paciente_id'])
        if not p:
            return jsonify({'erro':'Paciente não encontrado'}), 404
        ap.paciente_id = p.id
        
    # Atualiza procedimentos
    if data.get('procedimentos') is not None:
        proc_ids = data['procedimentos']
        if not isinstance(proc_ids, list) or len(proc_ids)==0:
            return jsonify({'erro':'Deve existir pelo menos um procedimento associado'}), 400
            
        # remove old links
        AppointmentProcedure.query.filter_by(atendimento_id=ap.id).delete()
        proc_objs = []
        for pid in proc_ids:
            try:
                pid = int(pid)
            except (ValueError, TypeError):
                return jsonify({'erro':f'ID de procedimento inválido: {pid}'}), 400
                
            p = Procedure.query.get(pid)
            if not p:
                return jsonify({'erro':f'Procedimento id {pid} não encontrado'}), 404
            proc_objs.append(p)
            
            ap_proc = AppointmentProcedure(atendimento_id=ap.id, procedimento_id=p.id)
            db.session.add(ap_proc)
            
        # Marca para recálculo do valor total
        procedimentos_changed = True
        
    # Atualiza tipo
    if data.get('tipo'):
        tipo = data['tipo']
        if not is_valid_string(tipo) or tipo not in ['plano','particular']:
            return jsonify({'erro':'tipo deve ser "plano" ou "particular" e não pode ser vazio'}), 400
        ap.tipo = tipo.strip()
        
    # Atualiza numero_carteira
    if data.get('numero_carteira') is not None:
        numero_carteira = data['numero_carteira']
        # Se for fornecido, deve ser string válida
        if not is_valid_string(numero_carteira):
            # Se for fornecido mas estiver vazio, limpa o campo
            ap.numero_carteira = None 
        else:
            ap.numero_carteira = numero_carteira.strip()

    # Se o tipo é plano (após possíveis atualizações), o numero_carteira é obrigatório
    if ap.tipo == 'plano' and not ap.numero_carteira:
        return jsonify({'erro':'numero_carteira obrigatório para tipo plano'}), 400
        
    # Recalcula valor total se procedimentos ou tipo mudaram (ou se for o primeiro update de tipo)
    if procedimentos_changed or 'tipo' in data:
        # Se os procedimentos não foram atualizados explicitamente, carrega os atuais
        if not procedimentos_changed:
            proc_objs = [ap_proc.procedimento for ap_proc in ap.procedimentos_vinculados]
            
        # Recalcula com o tipo atualizado
        ap.valor_total = calc_valor_total(proc_objs, ap.tipo)
        
    db.session.commit()
    return jsonify(ap.to_dict()), 200

@appointments_bp.route('/<int:ap_id>', methods=['DELETE'])
@auth_required
def delete_appointment(ap_id):
    ap = Appointment.query.get_or_404(ap_id)
    
    # only creator or admin
    if request.user.get('tipo') != 'admin' and request.user.get('id') != ap.usuario_id:
        return jsonify({'erro':'Apenas criador ou admin pode remover atendimento'}), 403
        
    # delete linked procedures then appointment
    from models.appointment_model import AppointmentProcedure
    AppointmentProcedure.query.filter_by(atendimento_id=ap.id).delete()
    db.session.delete(ap)
    db.session.commit()
    return jsonify({'mensagem':'Atendimento removido'}), 200

@appointments_bp.route('/between', methods=['GET'])
@auth_required
def list_between_dates():
    # expects ?start=YYYY-MM-DD&end=YYYY-MM-DD
    start = request.args.get('start')
    end = request.args.get('end')
    
    # Validação de string não vazia para os argumentos de URL
    if not is_valid_string(start) or not is_valid_string(end):
        return jsonify({'erro':'Parâmetros start e end obrigatórios e não podem ser vazios'}), 400
        
    start_cleaned = start.strip()
    end_cleaned = end.strip()
    
    try:
        # Usamos fromisoformat que pode aceitar YYYY-MM-DD ou YYYY-MM-DDTHH:MM:SS
        s = datetime.fromisoformat(start_cleaned)
        e = datetime.fromisoformat(end_cleaned)
        
        # Se o formato for apenas YYYY-MM-DD, é bom garantir que 'end' seja no final do dia
        if len(end_cleaned) == 10:
            e = e.replace(hour=23, minute=59, second=59)

    except:
        return jsonify({'erro':'Formato de data inválido, use ISO (YYYY-MM-DD ou YYYY-MM-DDTHH:MM:SS)'}), 400
        
    query = Appointment.query.filter(Appointment.data_hora >= s, Appointment.data_hora <= e).order_by(Appointment.data_hora)
    return jsonify(paginate_query(query, lambda a: a.to_dict())), 200