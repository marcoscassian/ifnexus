from extensions import db

class Link(db.Model):
    __tablename__ = 'links'

    id = db.Column(db.Integer, primary_key=True)
    url = db.Column(db.Text, nullable=False)
    tipo = db.Column(db.String(30), nullable=False, default='outro')
    ordem = db.Column(db.Integer, nullable=False, default=0)
    projeto_id = db.Column(db.Integer, db.ForeignKey('projetos.id'), nullable=False)
