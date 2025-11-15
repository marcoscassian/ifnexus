from flask import Flask, render_template, url_for, request, flash, redirect
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
    Link
)


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

@app.route('/criarprojeto', methods=['GET','POST'])
@login_required
def criar_projeto():
    if request.method == 'POST':
        titulo = request.form.get('titulo')
        subtitulo = request.form.get('subtitulo')
        descricao = request.form.get('descricao')
        tipo = request.form.get('tipo')
        curso = request.form.get('curso')

        if not titulo or not descricao or not curso:
            flash('Preencha todos os campos obrigatórios!', 'error')
            return redirect(url_for('criar_projeto'))

        novo_projeto = Projeto(
            titulo=titulo,
            subtitulo=subtitulo,
            descricao=descricao,
            tipo=tipo,
            curso=curso,
            usuario_id=current_user.id
        )
        db.session.add(novo_projeto)
        db.session.flush()

        arquivo = request.files.get('arquivo')
        if arquivo and arquivo.filename:
            nome_pdf = secure_filename(arquivo.filename)
            caminho_pdf = os.path.join(app.config['UPLOAD_FOLDER_PDF'], nome_pdf)
            arquivo.save(caminho_pdf)
            novo_projeto.arquivo = nome_pdf

        imagens = request.files.getlist('imagens[]')
        lista_imagens = []

        for img in imagens:
            if img and img.filename:
                nome_img = secure_filename(img.filename)
                caminho_img = os.path.join(app.config['UPLOAD_FOLDER_IMG'], nome_img)
                img.save(caminho_img)
                lista_imagens.append(nome_img)

        novo_projeto.estrutura = ",".join(lista_imagens)

        nomes_autores = request.form.getlist('autor_nome[]')
        matriculas_autores = request.form.getlist('autor_matricula[]')
        tipos_autores = request.form.getlist('autor_tipo[]')

        for nome, matricula, tipo in zip(nomes_autores, matriculas_autores, tipos_autores):
            if nome.strip() and matricula.strip() and tipo.strip():
                autor = Autor(nome=nome, matricula=matricula, tipo=tipo, projeto_id=novo_projeto.id)
                db.session.add(autor)

        objetivos = request.form.getlist('objetivos[]')
        for obj in objetivos:
            if obj.strip():
                db.session.add(Objetivo(descricao=obj, projeto_id=novo_projeto.id))

        metodologias = request.form.getlist('metodologias[]')
        for met in metodologias:
            if met.strip():
                db.session.add(Metodologia(descricao=met, projeto_id=novo_projeto.id))

        links_principais = request.form.getlist('links_principais[]')
        for link in links_principais:
            if link.strip():
                db.session.add(Link(url=link, projeto_id=novo_projeto.id))

        links_extras = request.form.getlist('links[]')
        for link in links_extras:
            if link.strip():
                db.session.add(Link(url=link, projeto_id=novo_projeto.id))

        try:
            db.session.commit()
            flash('Projeto cadastrado com sucesso!', 'success')
        except Exception as e:
            db.session.rollback()
            flash(f'Erro ao cadastrar projeto: {str(e)}', 'error') 

        return redirect(url_for('criar_projeto'))

    return render_template('criar_projeto.html')


@app.route("/projeto/<int:id>")
def ver_projeto(id):
    projeto = Projeto.query.get(id)
    if projeto:
        return render_template("listar_projeto.html", projeto=projeto)
    else:
        flash('Projeto não encontrado.', 'error')
        return redirect(url_for('index'))

@app.route("/projetoscurtidos")
def projetos_curtidos():
    return render_template("projetos_curtidos.html")

@app.route("/login_suap")
def login_suap():
    params = {
        "response_type": "code",
        "client_id": SUAP_CLIENT_ID,
        "redirect_uri": SUAP_REDIRECT_URI,
        "scope": "identificacao email",
    }

    return redirect(f"{SUAP_AUTH_URL}?{urlencode(params)}")

@app.route("/callback_suap")
def callback_suap():

    code = request.args.get("code")
    if not code:
        flash("Erro: nenhum código recebido do SUAP.", "error")
        return redirect(url_for("login"))

    data = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": SUAP_REDIRECT_URI,
        "client_id": SUAP_CLIENT_ID,
    }

    token_response = requests.post(SUAP_TOKEN_URL, data=data)

    if token_response.status_code != 200:
        flash(f"Erro ao obter token do SUAP: {token_response.text}", "error")
        return redirect(url_for("login"))

    access_token = token_response.json().get("access_token")

    # buscar dados do usuário
    headers = {"Authorization": f"Bearer {access_token}"}
    user_info = requests.get(SUAP_API_URL, headers=headers).json()

    email = user_info.get("email")
    nome = user_info.get("nome_usual") or user_info.get("nome")

    # verificar se já existe no banco
    usuario = Usuario.query.filter_by(email=email).first()

    if not usuario:
        # criar um usuário automático
        usuario = Usuario(
            nome=nome,
            email=email,
            senha=bcrypt.generate_password_hash("suap_login").decode('utf-8')
        )
        db.session.add(usuario)
        db.session.commit()

    login_user(usuario)
    flash("Login via SUAP realizado com sucesso!", "success")
    return redirect(url_for("index"))

if __name__ == '__main__':
    app.run(debug=True)
