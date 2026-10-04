from extensions import db


class ProjetoArquivo(db.Model):
    __tablename__ = 'projeto_arquivos'

    id = db.Column(db.Integer, primary_key=True)
    caminho = db.Column(db.Text, nullable=False)
    nome_original = db.Column(db.Text, nullable=False)
    extensao = db.Column(db.String(15), nullable=False)
    tamanho = db.Column(db.Integer, nullable=False, default=0)
    ordem = db.Column(db.Integer, nullable=False, default=0)
    projeto_id = db.Column(db.Integer, db.ForeignKey('projetos.id'), nullable=False, index=True)
