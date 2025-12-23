from flask import render_template, request, flash, redirect, url_for
from flask_login import login_user, logout_user, login_required, current_user

import requests
from urllib.parse import urlencode

from extensions import db, bcrypt
from models import Usuario, Comentario, Curtida
from . import auth_bp

from services.suap_config import *

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    
    if request.method == "POST":
        email = request.form.get('email')
        senha = request.form.get('senha')

        usuario = Usuario.query.filter_by(email=email).first()

        if usuario and bcrypt.check_password_hash(usuario.senha, senha):
            login_user(usuario)
            flash('Login realizado com sucesso!', 'success')
            return redirect(url_for('main.index'))
        else:
            flash('Email ou senha inválidos.', 'error')
            return redirect(url_for('auth.login'))

    return render_template('auth/login.html')

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    
    if request.method == 'POST':
        nome = request.form.get('name')
        email = request.form.get('email')
        senha = request.form.get('password')
        confirm = request.form.get('confirm_password')
        tipo_usuario = 'Visitante'

        if senha != confirm:
            flash("As senhas não coincidem.", "error")
            return redirect(url_for('auth.register'))

        if Usuario.query.filter_by(email=email).first():
            flash("Este email já está cadastrado.", "error")
            return redirect(url_for('auth.register'))

        senha_hash = bcrypt.generate_password_hash(senha).decode('utf-8')
        novo_usuario = Usuario(nome=nome, email=email, senha=senha_hash, tipo_usuario=tipo_usuario) 
        db.session.add(novo_usuario)
        db.session.commit()

        flash('Cadastro realizado com sucesso! Agora faça login.', 'success')
        return redirect(url_for('auth.login'))

    return render_template('auth/register.html')

@auth_bp.route('/logout')
@login_required
def logout():   
    
    logout_user()
    flash('Logout realizado com sucesso!', 'success')
    return redirect(url_for('index'))


@auth_bp.route("/login_suap")
def login_suap():
    
    params = {
        "response_type": "code",
        "client_id": SUAP_CLIENT_ID,
        "redirect_uri": SUAP_REDIRECT_URI,
    }

    return redirect(f"{SUAP_AUTH_URL}?{urlencode(params)}")

@auth_bp.route("/callback_suap")
def callback_suap():
    code = request.args.get("code")
    if not code:
        flash("Erro: nenhum código recebido do SUAP.", "error")
        return redirect(url_for("auth.login"))

    data = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": SUAP_REDIRECT_URI,
        "client_id": SUAP_CLIENT_ID,
    }

    token_response = requests.post(SUAP_TOKEN_URL, data=data)

    if token_response.status_code != 200:
        flash(f"Erro ao obter token do SUAP: {token_response.text}", "error")
        return redirect(url_for("auth.login"))

    access_token = token_response.json().get("access_token")

    headers = {
        "Authorization": f"Bearer {access_token}",
        "Accept": "application/json"
    }

    SUAP_API_URL = "https://suap.ifrn.edu.br/api/eu/"
    response = requests.get(SUAP_API_URL, headers=headers)

    if response.status_code != 200:
        print("STATUS SUAP:", response.status_code)
        print("RESPOSTA SUAP:", response.text)
        flash("Erro ao buscar dados do usuário no SUAP.", "error")
        return redirect(url_for("auth.login"))

    user_info = response.json()

    email = user_info.get("email")
    nome = user_info.get("nome_usual") or user_info.get("nome")
    vinculo = user_info.get("vinculo", {})
    print(user_info)
    suap_usuario = Usuario.query.filter_by(email=email).first()

    if not suap_usuario:
        print(user_info)
        suap_usuario = Usuario(
            nome=nome,
            email=email,
            senha=bcrypt.generate_password_hash("suap_login_default_123").decode("utf-8"),
            data_nascimento=user_info.get("data_de_nascimento"),
            cpf=user_info.get("cpf"),
            tipo_usuario=user_info.get("tipo_usuario"),
            matricula=user_info.get("identificacao"),
            campus=user_info.get("campus"),
            foto=user_info.get("foto")
        )

        db.session.add(suap_usuario)
        db.session.commit()

    if current_user.is_authenticated and current_user.id != suap_usuario.id:
        antigo = current_user

        for comentario in Comentario.query.filter_by(usuario_id=antigo.id).all():
            comentario.usuario_id = suap_usuario.id

        for curtida in Curtida.query.filter_by(usuario_id=antigo.id).all():
            curtida.usuario_id = suap_usuario.id

        db.session.commit()
        db.session.delete(antigo)
        db.session.commit()

    login_user(suap_usuario)
    flash("Login via SUAP realizado com sucesso!", "success")
    return redirect(url_for("main.index"))