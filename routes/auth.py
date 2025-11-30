from flask import Blueprint, request, jsonify
from app import db
from models.user_model import User
from utils.jwt_util import generate_token
from datetime import datetime

auth_bp = Blueprint('auth_bp', __name__)

# Função auxiliar para verificar se a string não está vazia (após strip).
# Reutilizada de outros arquivos para consistência.
def is_valid_string(value):
    """Retorna True se o valor for uma string não vazia (após strip), False caso contrário."""
    return isinstance(value, str) and bool(value.strip())

@auth_bp.route('/login', methods=['POST'])
def login():
    data = request.get_json() or {}
    email = data.get('email')
    senha = data.get('senha')
    
    # Validação de não-vazio
    if not is_valid_string(email) or not is_valid_string(senha):
        return jsonify({'erro':'Email e senha são obrigatórios e não podem ser vazios'}), 400
        
    email_cleaned = email.strip()
    
    user = User.query.filter_by(email=email_cleaned).first()
    
    # Validação de credenciais
    if not user or not user.check_password(senha):
        return jsonify({'erro':'Credenciais inválidas'}), 401
        
    token = generate_token(user.id, user.tipo)
    return jsonify({'token': token, 'usuario': user.to_dict()}), 200

@auth_bp.route('/register', methods=['POST'])
def register():
    data = request.get_json() or {}

    email = data.get('email')
    nome = data.get('nome')
    tipo = data.get('tipo', 'default')  # default se não enviar
    senha = data.get('senha')

    # Campos obrigatórios para o registro
    required_fields = {
        'email': 'Email',
        'nome': 'Nome',
        'tipo': 'Tipo',
        'senha': 'Senha'
    }

    # Validação de campos obrigatórios e não vazios
    for field, display_name in required_fields.items():
        value = data.get(field)
        if not is_valid_string(value):
            return jsonify({'erro': f'O campo {display_name} é obrigatório e não pode ser vazio'}), 400

    # Aplica strip nas strings
    email_cleaned = email.strip()
    nome_cleaned = nome.strip()
    tipo_cleaned = tipo.strip()
    
    # Validação de tipo
    if tipo_cleaned not in ['admin', 'default']:
        return jsonify({'erro': 'Tipo inválido (use admin ou default)'}), 400

    # check se email já existe
    if User.query.filter_by(email=email_cleaned).first():
        return jsonify({'erro': 'Email já cadastrado'}), 400

    # cria user
    user = User(
        email=email_cleaned,
        nome=nome_cleaned,
        tipo=tipo_cleaned
    )
    user.set_password(senha) # A senha não é stripada, pois espaços podem ser intencionais na senha

    db.session.add(user)
    db.session.commit()

    return jsonify({
        'mensagem': 'Usuário criado com sucesso',
        'usuario': user.to_dict()
    }), 201