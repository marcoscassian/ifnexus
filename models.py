from db import db
from flask_login import UserMixin

class Usuario(db.Model, UserMixin):
    __tablename__ = 'usuarios'

    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.Text, nullable=False)
    email = db.Column(db.Text, nullable=False)
    senha = db.Column(db.Text, nullable=False)
