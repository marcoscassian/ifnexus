from extensions import db

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
    curtidas = db.Column(db.Integer, default=0)
    
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'), nullable=False)
    autores = db.relationship('Autor', backref='projeto', lazy=True, cascade="all, delete-orphan")
    objetivos = db.relationship('Objetivo', backref='projeto', lazy=True, cascade="all, delete-orphan")
    metodologias = db.relationship('Metodologia', backref='projeto', lazy=True, cascade="all, delete-orphan")
    links = db.relationship('Link', backref='projeto', lazy=True, cascade="all, delete-orphan")
    comentarios = db.relationship('Comentario', backref='projeto', lazy=True, cascade="all, delete-orphan")