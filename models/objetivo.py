from extensions import db

class Objetivo(db.Model):
    __tablename__ = 'objetivos'

    id = db.Column(db.Integer, primary_key=True)
    descricao = db.Column(db.Text, nullable=False)
    ordem = db.Column(db.Integer, nullable=False, default=0)
    projeto_id = db.Column(db.Integer, db.ForeignKey('projetos.id'), nullable=False)
