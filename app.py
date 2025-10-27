from flask import Flask, render_template, url_for, request, flash, redirect
from flask_login import LoginManager, login_user, UserMixin, login_required, logout_user, current_user
from flask_bcrypt import Bcrypt
import os

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

        nomes_autores = request.form.getlist('autor_nome[]')
        matriculas_autores = request.form.getlist('autor_matricula[]')
        for nome, matricula in zip(nomes_autores, matriculas_autores):
            if nome.strip() and matricula.strip():
                autor = Autor(nome=nome, matricula=matricula, projeto_id=novo_projeto.id)
                db.session.add(autor)

        objetivos = request.form.getlist('objetivos[]')
        for obj in objetivos:
            if obj.strip():
                db.session.add(Objetivo(descricao=obj, projeto_id=novo_projeto.id))

        metodologias = request.form.getlist('metodologias[]')
        for met in metodologias:
            if met.strip():
                db.session.add(Metodologia(descricao=met, projeto_id=novo_projeto.id))

        links = request.form.getlist('links[]')
        for link in links:
            if link.strip():
                db.session.add(Link(url=link, projeto_id=novo_projeto.id))

        try:
            db.session.commit()
            flash('Projeto cadastrado com sucesso com todos os dados!', 'success')
        except Exception as e:
            db.session.rollback()
            flash(f'Erro ao cadastrar projeto: {str(e)}', 'error')

        return redirect(url_for('criar_projeto'))

    return render_template('criar_projeto.html')


@app.route('/listarprojeto')
def listar_projeto():
    projeto = db.session.query(Projeto).all()
    return render_template('listar_projeto.html', projeto=projeto)

if __name__ == '__main__':
    app.run(debug=True)
