from flask import render_template, request, flash, redirect, url_for, jsonify
from flask_login import login_user, logout_user, login_required, current_user

import json
from extensions import db, bcrypt
from models import Usuario, Comentario, Curtida
from . import auth_bp

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
    return redirect(url_for('main.index'))


@auth_bp.route('/login_suap')
def login_suap():
    """Rota que redireciona para a página de autenticação do SUAP"""
    # O JavaScript no login.html vai processar o retorno do SUAP
    return render_template('auth/login.html')


@auth_bp.route('/login_suap_js', methods=['POST'])
def login_suap_js():
    """Rota para processar login via SUAP através de JavaScript"""
    try:
        user_data = json.loads(request.form.get('user_data'))
        
        # Log dos dados recebidos
        print("Dados recebidos do SUAP:", user_data)
        
        # Buscar email (pode estar em diferentes campos)
        email = user_data.get("email") or user_data.get("email_institucional")
        
        # Buscar nome (pode estar em diferentes campos)
        nome = (user_data.get("nome_usual") or 
                user_data.get("nome_usu") or 
                user_data.get("nome") or
                user_data.get("apelido"))
        
        if not email or not nome:
            return jsonify({'success': False, 'message': 'Email ou nome não encontrado nos dados do SUAP'})
        
        suap_usuario = Usuario.query.filter_by(email=email).first()
        
        if not suap_usuario:
            # Criar novo usuário do SUAP
            suap_usuario = Usuario(
                nome=nome,
                email=email,
                senha=bcrypt.generate_password_hash("suap_login_default_123").decode("utf-8"),
                data_nascimento=user_data.get("data_de_nascimento") or user_data.get("data_nascimento"),
                cpf=user_data.get("cpf"),
                tipo_usuario="Aluno",  # Padrão para SUAP é Aluno
                matricula=user_data.get("matricula") or user_data.get("identificacao"),
                campus=user_data.get("campus") or user_data.get("unidade_organizacional"),
                foto=user_data.get("foto") or user_data.get("foto_78x100")
            )
            db.session.add(suap_usuario)
            db.session.commit()
            print(f"Novo usuário criado: {email}")
        
        # Fazer merge de usuários se necessário
        if current_user.is_authenticated and current_user.id != suap_usuario.id:
            antigo = current_user
            
            for comentario in Comentario.query.filter_by(usuario_id=antigo.id).all():
                comentario.usuario_id = suap_usuario.id
            
            for curtida in Curtida.query.filter_by(usuario_id=antigo.id).all():
                curtida.usuario_id = suap_usuario.id
            
            db.session.commit()
            db.session.delete(antigo)
            db.session.commit()
            print(f"Usuários mesclados: {antigo.id} -> {suap_usuario.id}")
        
        login_user(suap_usuario)
        print(f"Usuário {email} autenticado com sucesso")
        return jsonify({'success': True, 'message': 'Login via SUAP realizado com sucesso!'})
    
    except Exception as e:
        print(f"Erro ao fazer login SUAP: {str(e)}")
        return jsonify({'success': False, 'message': str(e)})