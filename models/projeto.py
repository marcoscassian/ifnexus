from extensions import db

projeto_tecnologias = db.Table(
    'projeto_tecnologias',
    db.Column('projeto_id', db.Integer, db.ForeignKey('projetos.id'), primary_key=True),
    db.Column('tecnologia_id', db.Integer, db.ForeignKey('tecnologias.id'), primary_key=True),
)

class Projeto(db.Model):
    __tablename__ = 'projetos'

    id = db.Column(db.Integer, primary_key=True)
    titulo = db.Column(db.Text, nullable=False)
    subtitulo = db.Column(db.Text)
    descricao = db.Column(db.Text, nullable=False)
    tipo = db.Column(db.Text)
    curso = db.Column(db.Text)
    status = db.Column(db.String(30), nullable=False, default='ideia')
    publicado = db.Column(db.Boolean, nullable=False, default=False, index=True)
    resultados = db.Column(db.Text)
    orientador_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'))
    estrutura = db.Column(db.Text)
    arquivo = db.Column(db.Text)
    curtidas = db.Column(db.Integer, default=0)
    
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'), nullable=False)
    autores = db.relationship('Autor', backref='projeto', lazy=True, cascade="all, delete-orphan")
    objetivos = db.relationship('Objetivo', backref='projeto', lazy=True, cascade="all, delete-orphan", order_by='Objetivo.ordem')
    metodologias = db.relationship('Metodologia', backref='projeto', lazy=True, cascade="all, delete-orphan", order_by='Metodologia.ordem')
    links = db.relationship('Link', backref='projeto', lazy=True, cascade="all, delete-orphan", order_by='Link.ordem')
    imagens = db.relationship('ProjetoImagem', backref='projeto', lazy=True, cascade="all, delete-orphan", order_by='ProjetoImagem.ordem')
    arquivos = db.relationship('ProjetoArquivo', backref='projeto', lazy=True, cascade="all, delete-orphan", order_by='ProjetoArquivo.ordem')
    tecnologias = db.relationship('Tecnologia', secondary=projeto_tecnologias, lazy='select', back_populates='projetos')
    orientador = db.relationship('Usuario', foreign_keys=[orientador_id])
    dono = db.relationship('Usuario', foreign_keys=[usuario_id])
    comentarios = db.relationship('Comentario', backref='projeto', lazy=True, cascade="all, delete-orphan")

    @property
    def imagem_capa(self):
        if self.imagens:
            return next((imagem for imagem in self.imagens if imagem.is_capa), self.imagens[0])
        return None

    @property
    def caminho_capa(self):
        capa = self.imagem_capa
        if capa:
            return capa.caminho
        if self.estrutura:
            return next((item for item in self.estrutura.split(',') if item), None)
        return None
