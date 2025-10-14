from flask import Flask, render_template, url_for, request, flash, session, redirect
from flask_login import LoginManager, login_user, UserMixin, login_required, logout_user
from flask_bcrypt import Bcrypt
from werkzeug.security import check_password_hash
from werkzeug.security import generate_password_hash

from models import (
    db,
    Usuario
    )

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///banco.db' #define a url do banco de dados sqlite
db.init_app(app) #Inicializa o db

bcrypt = Bcrypt(app)

#criação do banco de dados
with app.app_context():
    db.create_all()

app.secret_key = 'ifnexus'

login_manager = LoginManager()
login_manager.init_app(app)

@login_manager.user_loader
def load_user(user_id):
    return Usuario.query.get(int(user_id))

@app.route('/')
def index():
    cards = [
        {   
            "id": 1,
            "titulo": "IFNexus",
            "descricao": "O IFNexus é uma vitrine digital desenvolvida para divulgar e valorizar os projetos criados por estudantes e servidores do IFRN.",
            "imagem": "/static/img1.jpg",
            "tag": "Informática",
        },
        {
            "id": 2,
            "titulo": "SIMER",
            "descricao": "Sistema que monitora o consumo de energia em tempo real, identifica os maiores gastos e sugere formas de economizar.",
            "imagem": "/static/img2.jpg",
            "tag": "Eletrotécnica",
        },
        {
            "id": 3,
            "titulo": "EcoFios",
            "descricao": "Projeto voltado à produção de fios ecológicos reutilizando sobras de tecido. Busca reduzir o desperdício na indústria têxtil.",
            "imagem": "/static/img3.jpg",
            "tag": "Têxtil",
        },
        {
            "id": 4,
            "titulo": "Modus",
            "descricao": "Criação de roupas sustentáveis usando materiais ecológicos para reduzir o impacto ambiental da moda.",
            "imagem": "/static/img4.jpg",
            "tag": "Vestuário",
        },
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
            flash('Login realizado com sucesso!', category='success')
            return redirect(url_for('index'))
        else:
            flash('Email ou senha inválidos.', category='error')
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
            flash("As senhas não coincidem.", category="error")
            return redirect(url_for('register'))

        user_exists = Usuario.query.filter_by(email=email).first()
        if user_exists:
            flash("Este email já está cadastrado.", category= "error")
            return redirect(url_for("register"))

        senha_hash = bcrypt.generate_password_hash(senha).decode('utf-8')

        novo_usuario = Usuario(nome=nome, email=email, senha=senha_hash)
        db.session.add(novo_usuario)
        db.session.commit()

        flash('Cadastro realizado com sucesso! Agora faça login.', category='success')
        return redirect(url_for('login'))
    return render_template('register.html')
    
@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Logout realizado com sucesso!', category='success')
    return redirect(url_for('index'))


