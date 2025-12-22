from extensions import db
from flask_login import UserMixin

class Usuario(db.Model, UserMixin):
    __tablename__ = 'usuarios'

    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.Text, nullable=False)
    email = db.Column(db.Text, unique=True, nullable=False)
    senha = db.Column(db.Text, nullable=False)
    matricula = db.Column(db.Text)
    data_nascimento = db.Column(db.Text)
    cpf = db.Column(db.Text)
    tipo_usuario = db.Column(db.Text, nullable=False)
    campus = db.Column(db.Text)
    foto = db.Column(db.Text)
    comentarios = db.relationship('Comentario', backref='usuario', lazy=True, cascade="all, delete-orphan")