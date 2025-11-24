from flask import Flask, render_template, url_for, request, flash, redirect, jsonify
from flask_login import LoginManager, login_user, UserMixin, login_required, logout_user, current_user
from flask_bcrypt import Bcrypt
from werkzeug.utils import secure_filename
import os
import requests
from urllib.parse import urlencode

SUAP_CLIENT_ID = "G4IXTGHpxPafBmBGszCAuvxe6iBZgoK3W83HIUSE"
SUAP_REDIRECT_URI = "http://127.0.0.1:5000/callback_suap"
SUAP_AUTH_URL = "https://suap.ifrn.edu.br/o/authorize/"
SUAP_TOKEN_URL = "https://suap.ifrn.edu.br/o/token/"
SUAP_API_URL = "https://suap.ifrn.edu.br/api/v2/minhas-informacoes/meus-dados/"

from models import (
    db,
    Usuario,
    Projeto,
    Autor,
    Objetivo,
    Metodologia,
    Link,
    Comentario
)
from models import Curtida


app = Flask(__name__)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
app.config['UPLOAD_FOLDER_PDF'] = os.path.join(BASE_DIR, 'static', 'uploads', 'pdf')
app.config['UPLOAD_FOLDER_IMG'] = os.path.join(BASE_DIR, 'static', 'uploads', 'img')

ALLOWED_IMG_EXT = {'png', 'jpg', 'jpeg'}

os.makedirs(app.config['UPLOAD_FOLDER_PDF'], exist_ok=True)
os.makedirs(app.config['UPLOAD_FOLDER_IMG'], exist_ok=True)


app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///banco.db'
app.secret_key = 'ifnexus'

db.init_app(app)
bcrypt = Bcrypt(app)

with app.app_context():
    db.create_all()

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"

@login_manager.user_loader
def load_user(user_id):
    return Usuario.query.get(int(user_id))

@app.route('/')
def index():
    cards = [
        { "id": 1, "titulo": "IFNexus", "descricao": "O IFNexus é uma vitrine digital desenvolvida para divulgar e valorizar os projetos criados por estudantes e servidores do IFRN.", "imagem": "/static/img1.jpg", "tag": "Informática" },
        { "id": 2, "titulo": "SIMER", "descricao": "Sistema que monitora o consumo de energia em tempo real, identifica os maiores gastos e sugere formas de economizar.", "imagem": "/static/img2.jpg", "tag": "Eletrotécnica" },
        { "id": 3, "titulo": "EcoFios", "descricao": "Projeto voltado à produção de fios ecológicos reutilizando sobras de tecido. Busca reduzir o desperdício na indústria têxtil.", "imagem": "/static/img3.jpg", "tag": "Têxtil" },
        { "id": 4, "titulo": "Modus", "descricao": "Criação de roupas sustentáveis usando materiais ecológicos para reduzir o impacto ambiental da moda.", "imagem": "/static/img4.jpg", "tag": "Vestuário" },
    ]
    return render_template('index.html', cards=cards)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == "POST":
        email = request.form.get('email')
        senha = request.form.get('senha')

        usuario = Usuario.query.filter_by(email=email).first()

        if usuario and bcrypt.check_password_hash(usuario.senha, senha):
            login_user(usuario)
            flash('Login realizado com sucesso!', 'success')
            return redirect(url_for('index'))
        else:
            flash('Email ou senha inválidos.', 'error')
            return redirect(url_for('login'))

    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        nome = request.form.get('name')
        email = request.form.get('email')
        senha = request.form.get('password')
        confirm = request.form.get('confirm_password')

        if senha != confirm:
            flash("As senhas não coincidem.", "error")
            return redirect(url_for('register'))

        if Usuario.query.filter_by(email=email).first():
            flash("Este email já está cadastrado.", "error")
            return redirect(url_for('register'))

        senha_hash = bcrypt.generate_password_hash(senha).decode('utf-8')
        novo_usuario = Usuario(nome=nome, email=email, senha=senha_hash)
        db.session.add(novo_usuario)
        db.session.commit()

        flash('Cadastro realizado com sucesso! Agora faça login.', 'success')
        return redirect(url_for('login'))

    return render_template('register.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Logout realizado com sucesso!', 'success')
    return redirect(url_for('index'))

@app.route('/criarprojeto', methods=['GET','POST'], endpoint='criar_projeto')
@app.route('/editarprojeto/<int:id>', methods=['GET','POST'], endpoint='editar_projeto')
@login_required
def gerenciar_projeto(id=None):
    projeto = None
    if id:
        projeto = Projeto.query.get_or_404(id)
        if projeto.usuario_id != current_user.id:
            flash('Você não tem permissão para editar este projeto.', 'error')
            return redirect(url_for('meus_projetos'))
    
    if request.method == 'POST':
        is_edit = projeto is not None
        
        titulo = request.form.get('titulo')
        subtitulo = request.form.get('subtitulo')
        descricao = request.form.get('descricao')
        tipo = request.form.get('tipo')
        curso = request.form.get('curso')

        if not titulo or not descricao or not curso:
            flash('Preencha todos os campos obrigatórios!', 'error')
            return redirect(request.url)

        if not projeto:
            projeto = Projeto(
                titulo=titulo,
                subtitulo=subtitulo,
                descricao=descricao,
                tipo=tipo,
                curso=curso,
                usuario_id=current_user.id
            )
            db.session.add(projeto)
            db.session.flush()

        else:
            projeto.titulo = titulo
            projeto.subtitulo = subtitulo
            projeto.descricao = descricao
            projeto.tipo = tipo
            projeto.curso = curso
            
            Autor.query.filter_by(projeto_id=projeto.id).delete()
            Objetivo.query.filter_by(projeto_id=projeto.id).delete()
            Metodologia.query.filter_by(projeto_id=projeto.id).delete()
            Link.query.filter_by(projeto_id=projeto.id).delete()


        arquivo = request.files.get('arquivo')
        if arquivo and arquivo.filename:
            nome_pdf = secure_filename(arquivo.filename)
            caminho_pdf = os.path.join(app.config['UPLOAD_FOLDER_PDF'], nome_pdf)
            arquivo.save(caminho_pdf)
            projeto.arquivo = nome_pdf
        
        imagens = request.files.getlist('imagens[]')
        lista_imagens = []

        if any(img.filename for img in imagens):
             for img in imagens:
                if img and img.filename:
                    nome_img = secure_filename(img.filename)
                    caminho_img = os.path.join(app.config['UPLOAD_FOLDER_IMG'], nome_img)
                    img.save(caminho_img)
                    lista_imagens.append(nome_img)
             projeto.estrutura = ",".join(lista_imagens)

        nomes_autores = request.form.getlist('autor_nome[]')
        matriculas_autores = request.form.getlist('autor_matricula[]')
        tipos_autores = request.form.getlist('autor_tipo[]')

        for nome, matricula, tipo in zip(nomes_autores, matriculas_autores, tipos_autores):
            if nome.strip() and matricula.strip() and tipo.strip():
                autor = Autor(nome=nome, matricula=matricula, tipo=tipo, projeto_id=projeto.id)
                db.session.add(autor)

        objetivos = request.form.getlist('objetivos[]')
        for obj in objetivos:
            if obj.strip():
                db.session.add(Objetivo(descricao=obj, projeto_id=projeto.id))

        metodologias = request.form.getlist('metodologias[]')
        for met in metodologias:
            if met.strip():
                db.session.add(Metodologia(descricao=met, projeto_id=projeto.id))

        links_principais = request.form.getlist('links_principais[]')
        for link in links_principais:
            if link.strip():
                db.session.add(Link(url=link, projeto_id=projeto.id, tipo='principal'))

        links_extras = request.form.getlist('links[]')
        for link in links_extras:
             if link.strip():
                db.session.add(Link(url=link, projeto_id=projeto.id, tipo='extra'))


        db.session.commit()
        
        msg = 'Projeto atualizado com sucesso!' if is_edit else 'Projeto cadastrado com sucesso!'
        flash(msg, 'success')
        return redirect(url_for('ver_projeto', id=projeto.id))

    dados_projeto = {
        'titulo': projeto.titulo if projeto else '',
        'subtitulo': projeto.subtitulo if projeto else '',
        'descricao': projeto.descricao if projeto else '',
        'tipo': projeto.tipo if projeto else '',
        'curso': projeto.curso if projeto else '',
        'arquivo_nome': projeto.arquivo if projeto else '',
        'imagens': projeto.estrutura.split(',') if projeto and projeto.estrutura else ['','','',''],
        'autores': projeto.autores if projeto and projeto.autores else [Autor(nome='', matricula='', tipo=''), Autor(nome='', matricula='', tipo=''), Autor(nome='', matricula='', tipo='')],
        'objetivos': projeto.objetivos if projeto and projeto.objetivos else [Objetivo(descricao=''), Objetivo(descricao=''), Objetivo(descricao='')],
        'metodologias': projeto.metodologias if projeto and projeto.metodologias else [Metodologia(descricao=''), Metodologia(descricao=''), Metodologia(descricao='')],
        'link_principal': next((link.url for link in projeto.links if link.tipo == 'principal'), '') if projeto else '',
        'links_extras': [link.url for link in projeto.links if link.tipo == 'extra'] if projeto else [''],
        'action_url': url_for('editar_projeto', id=id) if id else url_for('criar_projeto'),
        'submit_text': 'Atualizar Projeto' if id else 'Cadastrar Projeto',
        'header_title': 'Editar Projeto' if id else 'Cadastrar Novo Projeto',
        'header_subtitle': 'Altere os dados abaixo para atualizar seu projeto.' if id else 'Preencha os dados abaixo para publicar seu projeto na vitrine do IF.'
    }

    return render_template('criar_projeto.html', **dados_projeto)

@app.route('/meus_projetos')
@login_required
def meus_projetos():
    projetos = Projeto.query.filter_by(usuario_id=current_user.id).all()
    return render_template('meus_projetos.html', projetos=projetos)

@app.route('/projeto/<int:id>')
def ver_projeto(id):
    projeto = Projeto.query.get_or_404(id)
    comentarios = Comentario.query.filter_by(projeto_id=id).order_by(Comentario.criado_em.desc()).all()
    
    liked = False
    if current_user.is_authenticated:
        liked = Curtida.query.filter_by(usuario_id=current_user.id, projeto_id=id).first() is not None

    static_path = os.path.join(BASE_DIR, 'static', 'img', 'interacoes', 'curtidas')
    heart_liked_exists = os.path.exists(os.path.join(static_path, 'heartliked.png'))
    heart_exists = os.path.exists(os.path.join(static_path, 'heart.png'))
    heart_hover_exists = os.path.exists(os.path.join(static_path, 'hearthover.png'))

    return render_template('listar_projeto.html', 
        projeto=projeto, 
        comentarios=comentarios, 
        liked=liked,
        heart_liked_exists=heart_liked_exists,
        heart_exists=heart_exists,
        heart_hover_exists=heart_hover_exists
    )

@app.route('/projeto/<int:id>/comentar', methods=['POST'])
@login_required
def adicionar_comentario(id):
    projeto = Projeto.query.get_or_404(id)
    conteudo = request.form.get('conteudo')

    if conteudo.strip():
        novo_comentario = Comentario(conteudo=conteudo, usuario_id=current_user.id, projeto_id=projeto.id)
        db.session.add(novo_comentario)
        db.session.commit()
        flash('Comentário adicionado!', 'success')
    else:
        flash('O comentário não pode ser vazio.', 'error')
        
    return redirect(url_for('ver_projeto', id=projeto.id))

@app.route('/projeto/<int:id>/curtir', methods=['POST'])
@login_required
def curtir_projeto(id):
    projeto = Projeto.query.get_or_404(id)
    curtida = Curtida.query.filter_by(usuario_id=current_user.id, projeto_id=id).first()
    
    if curtida:
        db.session.delete(curtida)
        projeto.curtidas = (projeto.curtidas or 1) - 1
        db.session.commit()
        return jsonify({'liked': False, 'curtidas': projeto.curtidas})
    else:
        nova_curtida = Curtida(usuario_id=current_user.id, projeto_id=id)
        db.session.add(nova_curtida)
        projeto.curtidas = (projeto.curtidas or 0) + 1
        db.session.commit()
        return jsonify({'liked': True, 'curtidas': projeto.curtidas})

@app.route('/projeto/<int:id>/excluir', methods=['POST'])
@login_required
def excluir_projeto(id):
    projeto = Projeto.query.get_or_404(id)
    if projeto.usuario_id != current_user.id:
        flash('Você não tem permissão para excluir este projeto.', 'error')
        return redirect(url_for('meus_projetos'))
    
    Autor.query.filter_by(projeto_id=id).delete()
    Objetivo.query.filter_by(projeto_id=id).delete()
    Metodologia.query.filter_by(projeto_id=id).delete()
    Link.query.filter_by(projeto_id=id).delete()
    Comentario.query.filter_by(projeto_id=id).delete()
    Curtida.query.filter_by(projeto_id=id).delete()
    
    db.session.delete(projeto)
    db.session.commit()
    
    flash('Projeto excluído com sucesso!', 'success')
    return redirect(url_for('meus_projetos'))
if __name__ == '__main__':
    app.run(debug=True)
