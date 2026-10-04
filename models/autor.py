from extensions import db

class Autor(db.Model):
    __tablename__ = 'autores'

    id = db.Column(db.Integer, primary_key=True)
    tipo = db.Column(db.String(50), nullable=False, default='coautor')

    usuario_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'))
    projeto_id = db.Column(db.Integer, db.ForeignKey('projetos.id'))

    usuario = db.relationship('Usuario')
