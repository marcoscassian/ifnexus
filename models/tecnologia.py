from extensions import db


class Tecnologia(db.Model):
    __tablename__ = 'tecnologias'

    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(80), nullable=False, unique=True, index=True)
    projetos = db.relationship('Projeto', secondary='projeto_tecnologias', back_populates='tecnologias')
