from app import db
from datetime import datetime

class Patient(db.Model):
    __tablename__ = 'pacientes'
    id = db.Column(db.Integer, primary_key=True)
    cpf = db.Column(db.String(14), unique=True, nullable=False)
    nome = db.Column(db.String(150), nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False)
    telefone = db.Column(db.String(30), nullable=False)
    data_nascimento = db.Column(db.Date, nullable=False)

    estado = db.Column(db.String(50), nullable=False)
    cidade = db.Column(db.String(50), nullable=False)
    bairro = db.Column(db.String(50), nullable=False)
    cep = db.Column(db.String(20), nullable=False)
    rua = db.Column(db.String(150), nullable=False)
    numero = db.Column(db.String(20), nullable=False)

    resp_cpf = db.Column(db.String(14), nullable=True)
    resp_nome = db.Column(db.String(150), nullable=True)
    resp_data_nascimento = db.Column(db.Date, nullable=True)
    resp_email = db.Column(db.String(150), nullable=True)
    resp_telefone = db.Column(db.String(30), nullable=True)

    atendimentos = db.relationship('Appointment', backref='paciente', lazy=True)

    def is_minor(self):
        today = datetime.today().date()
        age = (today - self.data_nascimento).days // 365
        return age < 18

    def responsible_is_adult(self):
        if not self.resp_data_nascimento:
            return False
        today = datetime.today().date()
        age = (today - self.resp_data_nascimento).days // 365
        return age >= 18

    def to_dict(self):
        data = {
            'id': self.id,
            'cpf': self.cpf,
            'nome': self.nome,
            'email': self.email,
            'telefone': self.telefone,
            'data_nascimento': self.data_nascimento.isoformat(),
            'endereco': {
                'estado': self.estado,
                'cidade': self.cidade,
                'bairro': self.bairro,
                'cep': self.cep,
                'rua': self.rua,
                'numero': self.numero
            }
        }
        if self.is_minor():
            data['responsavel'] = {
                'cpf': self.resp_cpf,
                'nome': self.resp_nome,
                'data_nascimento': self.resp_data_nascimento.isoformat() if self.resp_data_nascimento else None,
                'email': self.resp_email,
                'telefone': self.resp_telefone
            }
        return data
