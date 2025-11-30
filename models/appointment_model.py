from app import db
from datetime import datetime

class AppointmentProcedure(db.Model):
    __tablename__ = 'atendimento_procedimentos'
    id = db.Column(db.Integer, primary_key=True)
    atendimento_id = db.Column(db.Integer, db.ForeignKey('atendimentos.id'), nullable=False)
    procedimento_id = db.Column(db.Integer, db.ForeignKey('procedimentos.id'), nullable=False)

class Appointment(db.Model):
    __tablename__ = 'atendimentos'
    id = db.Column(db.Integer, primary_key=True)
    data_hora = db.Column(db.DateTime, nullable=False)
    tipo = db.Column(db.String(20), nullable=False)  # 'plano' or 'particular'
    numero_carteira = db.Column(db.String(100), nullable=True)
    valor_total = db.Column(db.Float, nullable=False, default=0.0)

    usuario_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'), nullable=False)
    paciente_id = db.Column(db.Integer, db.ForeignKey('pacientes.id'), nullable=False)

    procedimentos = db.relationship('AppointmentProcedure', backref='atendimento', lazy=True)

    def to_dict(self):
        return {
            'id': self.id,
            'data_hora': self.data_hora.isoformat(),
            'tipo': self.tipo,
            'numero_carteira': self.numero_carteira,
            'valor_total': self.valor_total,
            'usuario_id': self.usuario_id,
            'paciente_id': self.paciente_id,
            'procedimentos': [ap.procedimento.to_dict() for ap in self.procedimentos]
        }
