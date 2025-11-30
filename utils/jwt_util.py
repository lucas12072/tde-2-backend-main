import jwt
from flask import request, jsonify
from functools import wraps
from config import Config
from datetime import datetime, timedelta

def generate_token(user_id, tipo):
    payload = {
        'id': user_id,
        'tipo': tipo,
        'exp': datetime.utcnow() + timedelta(hours=8)
    }
    return jwt.encode(payload, Config.JWT_SECRET, algorithm='HS256')

def auth_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        auth = request.headers.get('Authorization', None)
        if not auth:
            return jsonify({'erro':'Token não fornecido'}), 401
        parts = auth.split()
        if parts[0].lower() != 'bearer' or len(parts)!=2:
            return jsonify({'erro':'Cabeçalho Authorization inválido'}), 401
        token = parts[1]
        try:
            payload = jwt.decode(token, Config.JWT_SECRET, algorithms=['HS256'])
        except jwt.ExpiredSignatureError:
            return jsonify({'erro':'Token expirado'}), 401
        except Exception:
            return jsonify({'erro':'Token inválido'}), 401
        # attach user info to request context (flask global)
        request.user = payload
        return fn(*args, **kwargs)
    return wrapper

def admin_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        # ensure authenticated first
        if not hasattr(request, 'user'):
            # try to run auth_required
            return auth_required(lambda *a, **k: fn(*a, **k))()
        if request.user.get('tipo') != 'admin':
            return jsonify({'erro':'Acesso de administrador necessário'}), 403
        return fn(*args, **kwargs)
    return wrapper
