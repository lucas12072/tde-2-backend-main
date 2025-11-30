from flask import Blueprint, request, jsonify
from app import db
from models.user_model import User
from utils.jwt_util import auth_required, admin_required
from utils.pagination import paginate_query
import re # Adicionado para validação de espaços em branco

users_bp = Blueprint('users_bp', __name__)

# Função auxiliar para verificar se a string não está vazia (após strip)
def is_valid_string(value):
    """Retorna True se o valor for uma string não vazia (após strip), False caso contrário."""
    return isinstance(value, str) and bool(value.strip())

@users_bp.route('/', methods=['GET'])
@auth_required
def list_users():
    # only admin
    from flask import request
    if request.user.get('tipo') != 'admin':
        return jsonify({'erro':'Acesso negado'}), 403
    query = User.query
    return jsonify(paginate_query(query, lambda u: u.to_dict())), 200

@users_bp.route('/', methods=['POST'])
@auth_required
def create_user():

    from flask import request
    # only admin can create
    if request.user.get('tipo') != 'admin':
        return jsonify({'erro':'Apenas admin pode cadastrar usuários'}), 403
        
    data = request.get_json() or {}
    
    email = data.get('email')
    nome = data.get('nome')
    tipo = data.get('tipo', 'default')
    senha = data.get('senha')
    
    # === INÍCIO DA VALIDAÇÃO DE CAMPOS NÃO VAZIOS ===
    # A validação agora exige que os campos sejam preenchidos E não contenham apenas espaços em branco.
    if not all([is_valid_string(email), is_valid_string(nome), is_valid_string(tipo), is_valid_string(senha)]):
        return jsonify({'erro':'email, nome, tipo, e senha são obrigatórios e não podem ser vazios'}), 400
    # === FIM DA VALIDAÇÃO DE CAMPOS NÃO VAZIOS ===
    
    # Normaliza os campos para remover espaços antes/depois, garantindo que o valor seja salvo corretamente
    email = email.strip()
    nome = nome.strip()
    tipo = tipo.strip()
    senha = senha.strip()
    
    if tipo not in ['admin','default']:
        return jsonify({'erro':'tipo inválido'}), 400
        
    if User.query.filter_by(email=email).first():
        return jsonify({'erro':'email já cadastrado'}), 400
        
    user = User(email=email, nome=nome, tipo=tipo)
    user.set_password(senha)
    db.session.add(user)
    db.session.commit()
    return jsonify(user.to_dict()), 201

@users_bp.route('/<int:user_id>', methods=['PUT'])
@auth_required
def update_user(user_id):
    from flask import request
    data = request.get_json() or {}
    user = User.query.get_or_404(user_id)
    
    # only admin or the user themself can edit
    if request.user.get('tipo') != 'admin' and request.user.get('id') != user.id:
        return jsonify({'erro':'Permitido apenas editar próprio usuário ou admin'}), 403
        
    nome = data.get('nome')
    email = data.get('email')
    
    # Validação para o campo 'email' no PUT:
    if email is not None:
        if not is_valid_string(email):
            return jsonify({'erro':'O campo email não pode ser vazio'}), 400
        
        # Normaliza o valor para uso
        email = email.strip()
        
        if email != user.email:
            if User.query.filter_by(email=email).first():
                return jsonify({'erro':'email já cadastrado'}), 400
            user.email = email
            
    # Validação para o campo 'nome' no PUT:
    if nome is not None:
        if not is_valid_string(nome):
            return jsonify({'erro':'O campo nome não pode ser vazio'}), 400
            
        # Normaliza e atualiza
        user.nome = nome.strip()
        
    db.session.commit()
    return jsonify(user.to_dict()), 200

@users_bp.route('/<int:user_id>', methods=['DELETE'])
@auth_required
def delete_user(user_id):
    from models.appointment_model import Appointment
    user = User.query.get_or_404(user_id)
    # only admin can delete and only if no atendimentos
    if request.user.get('tipo') != 'admin':
        return jsonify({'erro':'Apenas admin pode remover usuários'}), 403
    linked = Appointment.query.filter_by(usuario_id=user.id).first()
    if linked:
        return jsonify({'erro':'Usuário possui atendimentos vinculados e não pode ser removido'}), 400
    db.session.delete(user)
    db.session.commit()
    return jsonify({'mensagem':'Usuário removido'}), 200

@users_bp.route('/<int:user_id>/reset-senha', methods=['POST'])
@auth_required
def reset_password(user_id):
    # only admin can reset passwords
    if request.user.get('tipo') != 'admin':
        return jsonify({'erro':'Apenas admin pode resetar senhas'}), 403
        
    data = request.get_json() or {}
    new = data.get('senha')
    
    # === VALIDAÇÃO DE SENHA NOVA NÃO VAZIA ===
    if not is_valid_string(new):
        return jsonify({'erro':'senha nova obrigatória e não pode ser vazia'}), 400
    # === FIM DA VALIDAÇÃO ===
    
    user = User.query.get_or_404(user_id)
    user.set_password(new.strip())
    db.session.commit()
    return jsonify({'mensagem':'Senha resetada'}), 200

@users_bp.route('/me/alterar-senha', methods=['POST'])
@auth_required
def change_password():
    from flask import request
    data = request.get_json() or {}
    old = data.get('senha_antiga')
    new = data.get('senha_nova')
    
    # === VALIDAÇÃO DE SENHAS NÃO VAZIAS ===
    if not all([is_valid_string(old), is_valid_string(new)]):
        return jsonify({'erro':'senha_antiga e senha_nova obrigatórias e não podem ser vazias'}), 400
    # === FIM DA VALIDAÇÃO ===
    
    old = old.strip()
    new = new.strip()
    
    user = User.query.get_or_404(request.user.get('id'))
    if not user.check_password(old):
        return jsonify({'erro':'senha antiga incorreta'}), 400
        
    user.set_password(new)
    db.session.commit()
    return jsonify({'mensagem':'Senha alterada'}), 200

@users_bp.route('/buscar', methods=['GET'])
@auth_required
def get_by_email():
    from flask import request
    email = request.args.get('email')
    
    # === VALIDAÇÃO DE EMAIL NÃO VAZIO ===
    if not is_valid_string(email):
        return jsonify({'erro':'email é obrigatório e não pode ser vazio'}), 400
    # === FIM DA VALIDAÇÃO ===
    
    email = email.strip()
    
    user = User.query.filter_by(email=email).first()
    if not user:
        return jsonify({'erro':'Usuário não encontrado'}), 404
        
    # only admin or own user
    if request.user.get('tipo') != 'admin' and request.user.get('id') != user.id:
        return jsonify({'erro':'Acesso negado'}), 403
        
    return jsonify(user.to_dict()), 200