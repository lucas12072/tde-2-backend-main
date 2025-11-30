from flask import Flask, jsonify
from flask_sqlalchemy import SQLAlchemy
from config import Config
from dotenv import load_dotenv
import os

load_dotenv()

db = SQLAlchemy()

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)
    db.init_app(app)
    with app.app_context():
        from models import user_model, patient_model, procedure_model, appointment_model
        db.create_all()
    # register blueprints
    from routes.auth import auth_bp
    from routes.users import users_bp
    from routes.patients import patients_bp
    from routes.procedures import procedures_bp
    from routes.appointments import appointments_bp

    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(users_bp, url_prefix='/usuarios')
    app.register_blueprint(patients_bp, url_prefix='/pacientes')
    app.register_blueprint(procedures_bp, url_prefix='/procedimentos')
    app.register_blueprint(appointments_bp, url_prefix='/atendimentos')

    @app.route('/')
    def index():
        return jsonify({'mensagem':'Clinica API funcionando'}), 200

    return app

if __name__ == '__main__':
    app = create_app()
    debug = os.getenv('FLASK_DEBUG', '1') == '1'
    app.run(host='0.0.0.0', port=5000, debug=debug)
