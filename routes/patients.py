from flask import Blueprint, request, jsonify
from app import db
from models.patient_model import Patient
from utils.jwt_util import auth_required
from utils.pagination import paginate_query
from datetime import datetime, date # Importado date explicitamente

patients_bp = Blueprint('patients_bp', __name__)

# Função auxiliar para verificar se a string não está vazia (após strip).
# Reutilizada de outros arquivos para consistência.
def is_valid_string(value):
    """Retorna True se o valor for uma string não vazia (após strip), False caso contrário."""
    return isinstance(value, str) and bool(value.strip())

def parse_date(date_str):
    return datetime.fromisoformat(date_str).date()

@patients_bp.route('/', methods=['POST'])
@auth_required
def create_patient():
    data = request.get_json() or {}
    
    # Todos os campos obrigatórios (incluindo strings)
    required_fields = {
        'cpf': 'CPF',
        'nome': 'Nome',
        'email': 'Email',
        'telefone': 'Telefone',
        'data_nascimento': 'Data de Nascimento',
        'estado': 'Estado',
        'cidade': 'Cidade',
        'bairro': 'Bairro',
        'cep': 'CEP',
        'rua': 'Rua',
        'numero': 'Número'
    }

    # Validação de campos obrigatórios e não vazios
    for field, display_name in required_fields.items():
        value = data.get(field)
        # Verifica se o campo está ausente OU se é uma string vazia/só com espaços
        if not value or (isinstance(value, str) and not is_valid_string(value)):
            return jsonify({'erro':f'Campo {display_name} obrigatório e não pode ser vazio'}), 400
            
    # Remove espaços em branco das strings que serão usadas
    data_cleaned = {k: v.strip() if isinstance(v, str) else v for k, v in data.items()}
    
    # check duplicates (usando os valores limpos)
    if Patient.query.filter_by(cpf=data_cleaned['cpf']).first():
        return jsonify({'erro':'CPF já cadastrado'}), 400
    if Patient.query.filter_by(email=data_cleaned['email']).first():
        return jsonify({'erro':'Email já cadastrado'}), 400
        
    # create
    try:
        pn = parse_date(data_cleaned['data_nascimento'])
    except Exception:
        return jsonify({'erro':'data_nascimento formato ISO (YYYY-MM-DD) esperado'}), 400
        
    patient = Patient(
        cpf=data_cleaned['cpf'],
        nome=data_cleaned['nome'],
        email=data_cleaned['email'],
        telefone=data_cleaned['telefone'],
        data_nascimento=pn,
        estado=data_cleaned['estado'],
        cidade=data_cleaned['cidade'],
        bairro=data_cleaned['bairro'],
        cep=data_cleaned['cep'],
        rua=data_cleaned['rua'],
        numero=data_cleaned['numero']
    )
    
    # if minor, responsible data required
    age = (date.today() - pn).days//365
    if age < 18:
        rfields = {
            'resp_cpf': 'CPF do Responsável',
            'resp_nome': 'Nome do Responsável',
            'resp_data_nascimento': 'Data de Nascimento do Responsável',
            'resp_email': 'Email do Responsável',
            'resp_telefone': 'Telefone do Responsável'
        }
        for f, display_name in rfields.items():
            value = data.get(f)
            # Validação de campo obrigatório e não vazio para responsável
            if not value or (isinstance(value, str) and not is_valid_string(value)):
                return jsonify({'erro':f'Paciente menor: campo {display_name} obrigatório e não pode ser vazio'}), 400
        
        # Remove espaços em branco dos dados do responsável
        resp_data_cleaned = {k: v.strip() for k, v in data.items() if k in rfields}

        try:
            rd = parse_date(resp_data_cleaned['resp_data_nascimento'])
        except Exception:
            return jsonify({'erro':'resp_data_nascimento formato ISO (YYYY-MM-DD) esperado'}), 400
            
        # responsible cannot be minor
        r_age = (date.today() - rd).days//365
        if r_age < 18:
            return jsonify({'erro':'Responsável não pode ser menor de idade'}), 400
            
        patient.resp_cpf = resp_data_cleaned['resp_cpf']
        patient.resp_nome = resp_data_cleaned['resp_nome']
        patient.resp_data_nascimento = rd
        patient.resp_email = resp_data_cleaned['resp_email']
        patient.resp_telefone = resp_data_cleaned['resp_telefone']
        
    db.session.add(patient)
    db.session.commit()
    return jsonify(patient.to_dict()), 201

@patients_bp.route('/<int:patient_id>', methods=['PUT'])
@auth_required
def update_patient(patient_id):
    data = request.get_json() or {}
    patient = Patient.query.get_or_404(patient_id)
    
    # Campos de string que, se fornecidos, não podem ser vazios.
    string_fields = ['cpf', 'nome', 'email', 'telefone', 'estado', 'cidade', 'bairro', 'cep', 'rua', 'numero']
    
    # Processa e valida todos os campos de string
    for field in string_fields:
        if field in data:
            value = data[field]
            
            # === VALIDAÇÃO DE NÃO VAZIO ===
            if not is_valid_string(value):
                return jsonify({'erro':f'O campo {field} não pode ser vazio'}), 400
            # === FIM DA VALIDAÇÃO ===

            cleaned_value = value.strip()
            
            # Previne duplicidade de CPF/Email
            if field == 'cpf' and cleaned_value != patient.cpf:
                if Patient.query.filter_by(cpf=cleaned_value).first():
                    return jsonify({'erro':'CPF já cadastrado'}), 400
                patient.cpf = cleaned_value
            elif field == 'email' and cleaned_value != patient.email:
                if Patient.query.filter_by(email=cleaned_value).first():
                    return jsonify({'erro':'Email já cadastrado'}), 400
                patient.email = cleaned_value
            # Atualiza outros campos
            elif field != 'cpf' and field != 'email':
                setattr(patient, field, cleaned_value)
    
    if data.get('data_nascimento'):
        # Data de Nascimento deve ser uma string não vazia para ser processada
        if not is_valid_string(data['data_nascimento']):
            return jsonify({'erro':'O campo data_nascimento não pode ser vazio'}), 400

        try:
            patient.data_nascimento = parse_date(data['data_nascimento'].strip())
        except:
            return jsonify({'erro':'data_nascimento formato ISO (YYYY-MM-DD) esperado'}), 400
            
    # Atualiza dados do responsável (não implementado aqui, mas os dados não devem ser vazios se fornecidos)
    # NOTE: O código original não tratava a atualização dos dados do responsável no PUT.
    # Se precisar atualizar o responsável, a lógica de validação de 'is_valid_string' deve ser aplicada a cada campo de responsável antes de salvar.

    # handle responsible removal only if patient adult
    if 'remove_responsavel' in data and data.get('remove_responsavel')==True:
        # A validação de menoridade deve ser feita APÓS a potencial atualização de data_nascimento
        from datetime import date
        age_after_update = (date.today() - patient.data_nascimento).days//365
        
        if age_after_update < 18:
            return jsonify({'erro':'Não é possível remover responsável enquanto paciente for menor'}), 400
            
        patient.resp_cpf = None
        patient.resp_nome = None
        patient.resp_data_nascimento = None
        patient.resp_email = None
        patient.resp_telefone = None
        
    db.session.commit()
    return jsonify(patient.to_dict()), 200

@patients_bp.route('/<int:patient_id>', methods=['DELETE'])
@auth_required
def delete_patient(patient_id):
    from models.appointment_model import Appointment
    patient = Patient.query.get_or_404(patient_id)
    linked = Appointment.query.filter_by(paciente_id=patient.id).first()
    if linked:
        return jsonify({'erro':'Paciente possui atendimentos vinculados e não pode ser removido'}), 400
    db.session.delete(patient)
    db.session.commit()
    return jsonify({'mensagem':'Paciente removido'}), 200

@patients_bp.route('/<int:patient_id>', methods=['GET'])
@auth_required
def get_patient(patient_id):
    patient = Patient.query.get_or_404(patient_id)
    return jsonify(patient.to_dict()), 200

@patients_bp.route('/', methods=['GET'])
@auth_required
def list_patients():
    query = Patient.query.order_by(Patient.id)
    return jsonify(paginate_query(query, lambda p: p.to_dict())), 200