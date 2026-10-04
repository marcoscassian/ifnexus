from flask import current_app, render_template, request, flash, redirect, url_for, jsonify
from flask_login import login_user, logout_user, login_required

import secrets
import requests
from extensions import db, bcrypt
from models import Usuario
from . import auth_bp


def _suap_template_config():
    redirect_uri = current_app.config.get('SUAP_REDIRECT_URI') or url_for('auth.login', _external=True)
    return {
        'client_id': current_app.config.get('SUAP_CLIENT_ID', ''),
        'redirect_uri': redirect_uri,
        'base_url': current_app.config.get('SUAP_BASE_URL', 'https://suap.ifrn.edu.br'),
        'scope': current_app.config.get('SUAP_SCOPE', 'identificacao email'),
        'process_url': url_for('auth.login_suap_js'),
    }


def _first_value(data, *keys):
    for key in keys:
        value = data.get(key)
        if value not in (None, '', [], {}):
            return value
    return None


def _text_value(value):
    if isinstance(value, dict):
        value = value.get('nome') or value.get('descricao') or value.get('sigla')
    if isinstance(value, (list, tuple)):
        value = ', '.join(str(item) for item in value if item)
    return str(value).strip() if value not in (None, '') else None


def _authenticate_suap_user(user_data):
    email = _text_value(_first_value(
        user_data, 'email', 'email_preferencial', 'email_academico',
        'email_institucional', 'email_secundario'
    ))
    nome = _text_value(_first_value(
        user_data, 'nome_usual', 'nome_social', 'nome_registro',
        'nome_usu', 'nome', 'apelido'
    ))

    if not email or not nome:
        return None, 'O SUAP não retornou nome e e-mail suficientes para concluir o login.'

    email = email.lower()
    usuario = Usuario.query.filter_by(email=email).first()
    if not usuario:
        usuario = Usuario(
            nome=nome,
            email=email,
            senha=bcrypt.generate_password_hash(secrets.token_urlsafe(32)).decode('utf-8'),
            tipo_usuario=_text_value(user_data.get('tipo_usuario')) or 'Aluno',
        )
        db.session.add(usuario)

    usuario.nome = nome
    usuario.data_nascimento = _text_value(_first_value(user_data, 'data_de_nascimento', 'data_nascimento'))
    usuario.cpf = _text_value(user_data.get('cpf'))
    usuario.matricula = _text_value(_first_value(user_data, 'matricula', 'identificacao'))
    usuario.campus = _text_value(_first_value(user_data, 'campus', 'unidade_organizacional'))
    usuario.foto = _text_value(_first_value(user_data, 'foto', 'foto_78x100'))

    db.session.commit()
    login_user(usuario)
    return usuario, None

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

    return render_template('auth/login.html', suap_config=_suap_template_config())

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
    return redirect(url_for('main.index'))


@auth_bp.route('/login_suap')
def login_suap():
    """Mantém compatibilidade com links antigos e inicia o fluxo pela tela de login."""
    return redirect(url_for('auth.login'))


@auth_bp.route('/login_suap_js', methods=['POST'])
def login_suap_js():
    """Valida o token diretamente no SUAP antes de criar a sessão local."""
    try:
        payload = request.get_json(silent=True) or request.form
        access_token = payload.get('access_token')
        if not access_token:
            return jsonify({'success': False, 'message': 'Token do SUAP ausente.'}), 400

        suap_url = current_app.config.get('SUAP_BASE_URL', 'https://suap.ifrn.edu.br')
        response = requests.get(
            f"{suap_url}/api/rh/eu/",
            headers={'Authorization': f'Bearer {access_token}', 'Accept': 'application/json'},
            timeout=12,
        )
        if response.status_code in (401, 403):
            return jsonify({'success': False, 'message': 'O SUAP recusou ou expirou a autenticação.'}), 401
        response.raise_for_status()

        user_data = response.json()
        usuario, error = _authenticate_suap_user(user_data)
        if error:
            db.session.rollback()
            return jsonify({'success': False, 'message': error}), 422

        return jsonify({
            'success': True,
            'message': 'Login via SUAP realizado com sucesso!',
            'redirect': url_for('main.index'),
            'usuario_id': usuario.id,
        })
    except (requests.RequestException, ValueError):
        db.session.rollback()
        current_app.logger.exception('Falha ao validar o token no SUAP')
        return jsonify({'success': False, 'message': 'Não foi possível validar sua conta no SUAP agora.'}), 502
    except Exception:
        db.session.rollback()
        current_app.logger.exception('Erro inesperado no login SUAP')
        return jsonify({'success': False, 'message': 'Não foi possível concluir o login via SUAP.'}), 500
