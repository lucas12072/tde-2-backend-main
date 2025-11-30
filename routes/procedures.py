from flask import Blueprint, request, jsonify
from app import db
from models.procedure_model import Procedure
from models.appointment_model import AppointmentProcedure, Appointment
from utils.jwt_util import auth_required
from utils.pagination import paginate_query
# import re # Não é necessário se usarmos apenas a função is_valid_string

procedures_bp = Blueprint('procedures_bp', __name__)

# Função auxiliar para verificar se a string não está vazia (após strip)
def is_valid_string(value):
    """Retorna True se o valor for uma string não vazia (após strip), False caso contrário."""
    return isinstance(value, str) and bool(value.strip())

@procedures_bp.route('/', methods=['POST'])
@auth_required
def create_procedure():
    if request.user.get('tipo') != 'admin':
        return jsonify({'erro':'Apenas admin pode criar procedimentos'}), 403
    
    data = request.get_json() or {}
    required_string_fields = ['nome','descricao']
    required_value_fields = ['valor_plano','valor_particular']

    # === INÍCIO DA VALIDAÇÃO DE CAMPOS NÃO VAZIOS (String) ===
    for f in required_string_fields:
        value = data.get(f)
        if not is_valid_string(value):
            return jsonify({'erro':f'Campo {f} é obrigatório e não pode ser vazio'}), 400
            
    # === VALIDAÇÃO DE CAMPOS OBRIGATÓRIOS (Numéricos) ===
    for f in required_value_fields:
        if data.get(f) is None:
            return jsonify({'erro':f'Campo {f} obrigatório'}), 400
            
    # Aplica strip nas strings antes de usar
    nome = data['nome'].strip()
    descricao = data['descricao'].strip()
    
    if Procedure.query.filter_by(nome=nome).first():
        return jsonify({'erro':'Nome de procedimento já existe'}), 400
        
    try:
        valor_plano = float(data['valor_plano'])
        valor_particular = float(data['valor_particular'])
    except (ValueError, TypeError):
        return jsonify({'erro':'Valores de plano e particular devem ser números válidos'}), 400
        
    proc = Procedure(
        nome=nome,
        descricao=descricao,
        valor_plano=valor_plano,
        valor_particular=valor_particular
    )
    
    db.session.add(proc)
    db.session.commit()
    return jsonify(proc.to_dict()), 201

@procedures_bp.route('/<int:proc_id>', methods=['PUT'])
@auth_required
def update_procedure(proc_id):
    if request.user.get('tipo') != 'admin':
        return jsonify({'erro':'Apenas admin pode editar procedimentos'}), 403
        
    proc = Procedure.query.get_or_404(proc_id)
    data = request.get_json() or {}
    
    # Lista de campos que, se presentes, não podem ser vazios
    fields_to_validate = {
        'nome': str,
        'descricao': str,
        'valor_plano': (int, float),
        'valor_particular': (int, float)
    }

    # Validação do campo 'nome'
    if 'nome' in data and data['nome'] != proc.nome:
        if not is_valid_string(data['nome']):
            return jsonify({'erro':'O campo nome não pode ser vazio'}), 400
            
        new_nome = data['nome'].strip()
        
        if Procedure.query.filter_by(nome=new_nome).first():
            return jsonify({'erro':'Nome de procedimento já existe'}), 400
            
        proc.nome = new_nome

    # Validação dos demais campos
    for field, expected_type in fields_to_validate.items():
        if field in data and field != 'nome': # 'nome' já foi tratado acima
            value = data[field]
            
            # Validação de não-vazio para strings
            if expected_type is str:
                if not is_valid_string(value):
                    return jsonify({'erro':f'O campo {field} não pode ser vazio'}), 400
                setattr(proc, field, value.strip()) # Aplica strip e salva
                
            # Validação de tipo para valores numéricos
            elif expected_type == (int, float):
                try:
                    # Tenta converter o valor para float
                    numeric_value = float(value)
                    # Não aceita NaN, Inf
                    if numeric_value != numeric_value or numeric_value == float('inf') or numeric_value == float('-inf'):
                         return jsonify({'erro':f'O campo {field} possui um valor inválido'}), 400
                    setattr(proc, field, numeric_value)
                except (ValueError, TypeError):
                    return jsonify({'erro':f'O campo {field} deve ser um número válido'}), 400
                    
    db.session.commit()
    return jsonify(proc.to_dict()), 200

@procedures_bp.route('/<int:proc_id>', methods=['DELETE'])
@auth_required
def delete_procedure(proc_id):
    if request.user.get('tipo') != 'admin':
        return jsonify({'erro':'Apenas admin pode remover procedimentos'}), 403
        
    # do not remove if used in atendimentos
    used = AppointmentProcedure.query.filter_by(procedimento_id=proc_id).first()
    if used:
        return jsonify({'erro':'Procedimento já utilizado em atendimentos e não pode ser removido'}), 400
        
    proc = Procedure.query.get_or_404(proc_id)
    db.session.delete(proc)
    db.session.commit()
    return jsonify({'mensagem':'Procedimento removido'}), 200

@procedures_bp.route('/<int:proc_id>', methods=['GET'])
@auth_required
def get_procedure(proc_id):
    proc = Procedure.query.get_or_404(proc_id)
    return jsonify(proc.to_dict()), 200

@procedures_bp.route('/', methods=['GET'])
@auth_required
def list_procedures():
    query = Procedure.query.order_by(Procedure.id)
    return jsonify(paginate_query(query, lambda p: p.to_dict())), 200