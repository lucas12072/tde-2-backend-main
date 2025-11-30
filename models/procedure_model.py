from app import db

class Procedure(db.Model):
    __tablename__ = 'procedimentos'
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(150), unique=True, nullable=False)
    descricao = db.Column(db.Text, nullable=False)
    valor_plano = db.Column(db.Float, nullable=False)
    valor_particular = db.Column(db.Float, nullable=False)

    itens = db.relationship('AppointmentProcedure', backref='procedimento', lazy=True)

    def to_dict(self):
        return {
            'id': self.id,
            'nome': self.nome,
            'descricao': self.descricao,
            'valor_plano': self.valor_plano,
            'valor_particular': self.valor_particular
        }
