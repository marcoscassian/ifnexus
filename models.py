from flask_sqlalchemy import SQLAlchemy 
from flask_login import UserMixin
db = SQLAlchemy()

class Usuario(db.Model, UserMixin):
    __tablename__ = 'usuarios'

    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.Text, nullable=False)
    email = db.Column(db.Text, unique=True, nullable=False)
    senha = db.Column(db.Text, nullable=False)

class Projeto(db.Model):
    __tablename__ = 'projetos'

    id = db.Column(db.Integer, primary_key=True)
    titulo = db.Column(db.Text, nullable=False)
    subtitulo = db.Column(db.Text)
    descricao = db.Column(db.Text, nullable=False)
    tipo = db.Column(db.Text)
    curso = db.Column(db.Text)
    estrutura = db.Column(db.Text)
    arquivo = db.Column(db.Text)
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'), nullable=False)

    autores = db.relationship('Autor', backref='projeto', lazy=True, cascade="all, delete-orphan")
    objetivos = db.relationship('Objetivo', backref='projeto', lazy=True, cascade="all, delete-orphan")
    metodologias = db.relationship('Metodologia', backref='projeto', lazy=True, cascade="all, delete-orphan")
    links = db.relationship('Link', backref='projeto', lazy=True, cascade="all, delete-orphan")

class Autor(db.Model):
    __tablename__ = 'autores'

    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.Text, nullable=False)
    matricula = db.Column(db.Text, nullable=False)
    tipo = db.Column(db.Text) 
    projeto_id = db.Column(db.Integer, db.ForeignKey('projetos.id'), nullable=False)

class Objetivo(db.Model):
    __tablename__ = 'objetivos'

    id = db.Column(db.Integer, primary_key=True)
    descricao = db.Column(db.Text, nullable=False)
    projeto_id = db.Column(db.Integer, db.ForeignKey('projetos.id'), nullable=False)

class Metodologia(db.Model):
    __tablename__ = 'metodologias'

    id = db.Column(db.Integer, primary_key=True)
    descricao = db.Column(db.Text, nullable=False)
    projeto_id = db.Column(db.Integer, db.ForeignKey('projetos.id'), nullable=False)

class Link(db.Model):
    __tablename__ = 'links'

    id = db.Column(db.Integer, primary_key=True)
    url = db.Column(db.Text, nullable=False)
    projeto_id = db.Column(db.Integer, db.ForeignKey('projetos.id'), nullable=False)
