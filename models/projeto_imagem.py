from extensions import db


class ProjetoImagem(db.Model):
    __tablename__ = 'projeto_imagens'

    id = db.Column(db.Integer, primary_key=True)
    caminho = db.Column(db.Text, nullable=False)
    nome_original = db.Column(db.Text)
    is_capa = db.Column(db.Boolean, nullable=False, default=False)
    ordem = db.Column(db.Integer, nullable=False, default=0)
    projeto_id = db.Column(db.Integer, db.ForeignKey('projetos.id'), nullable=False, index=True)
