from flask import Flask, render_template, url_for, request, flash, redirect, jsonify
from flask_login import LoginManager, login_user, UserMixin, login_required, logout_user, current_user
from flask_bcrypt import Bcrypt
from werkzeug.utils import secure_filename
import os
import shutil
import requests
from urllib.parse import urlencode
from decorator import suap_required
from datetime import datetime


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
    Comentario,
    Curtida
)

app = Flask(__name__)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

def criar_pastas_projeto(titulo):
    nome_pasta = secure_filename(titulo.lower().replace(" ", "-"))
    
    base = os.path.join(BASE_DIR, "static", "uploads", "projetos", nome_pasta)
    pasta_imagens = os.path.join(base, "imagens")
    pasta_pdfs = os.path.join(base, "pdfs")

    os.makedirs(pasta_imagens, exist_ok=True)
    os.makedirs(pasta_pdfs, exist_ok=True)

    return base, pasta_imagens, pasta_pdfs, nome_pasta

ALLOWED_IMG_EXT = {'png', 'jpg', 'jpeg'}

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
    projetos_top = Projeto.query.order_by(Projeto.curtidas.desc()).limit(4).all()
    
    cards = []
    for projeto in projetos_top:
        imgs = projeto.estrutura.split(',') if projeto.estrutura else []
        img_url = imgs[0] if imgs and imgs[0] else "/static/img1.jpg"
        
        cards.append({
            "id": projeto.id,
            "titulo": projeto.titulo,
            "descricao": projeto.descricao,
            "imagem": img_url,
            "tag": projeto.curso or "Sem curso"
        })
    
    # se houver menos de 4 projetos, preencher com dados padrão
    if len(cards) < 4:
        cards_padrao = [
            { "id": 1, "titulo": "IFNexus", "descricao": "O IFNexus é uma vitrine digital desenvolvida para divulgar e valorizar os projetos criados por estudantes e servidores do IFRN.", "tag": "Informatica" },
            { "id": 2, "titulo": "SIMER", "descricao": "Sistema que monitora o consumo de energia em tempo real, identifica os maiores gastos e sugere formas de economizar.", "tag": "eletro" },
            { "id": 3, "titulo": "EcoFios", "descricao": "Projeto voltado à produção de fios ecológicos reutilizando sobras de tecido. Busca reduzir o desperdício na indústria têxtil.", "tag": "textil" },
            { "id": 4, "titulo": "Modus", "descricao": "Criação de roupas sustentáveis usando materiais ecológicos para reduzir o impacto ambiental da moda.", "tag": "vestuario" },
        ]
        cards.extend(cards_padrao[len(cards):4])
    
    return render_template('index.html', cards=cards)

@app.route('/projetos')
def projetos():
    """Exibe vitrine com todos os projetos com paginação (12 por página)"""
    curso_filtro = request.args.get('curso', '').strip()
    tipo_filtro = request.args.get('tipo', '').strip()
    ordenacao = request.args.get('ordenacao', 'recente').strip()
    q = request.args.get('q', '').strip()
    pagina = request.args.get('pagina', 1, type=int)

    query = Projeto.query
    
    if curso_filtro and curso_filtro != 'todos':
        query = query.filter_by(curso=curso_filtro)
    
    if tipo_filtro and tipo_filtro != 'todos':
        query = query.filter_by(tipo=tipo_filtro)

    if q:
        like_q = f"%{q}%"
        query = query.outerjoin(Autor).filter(
            db.or_(
                Projeto.titulo.ilike(like_q),
                Projeto.descricao.ilike(like_q),
                Autor.nome.ilike(like_q)
            )
        ).distinct()

    if ordenacao == 'curtidas':
        query = query.order_by(Projeto.curtidas.desc(), Projeto.id.desc())
    else:
        query = query.order_by(Projeto.id.desc())

    total_projetos = query.count()
    projetos_por_pagina = 12
    total_paginas = (total_projetos + projetos_por_pagina - 1) // projetos_por_pagina

    pagina = max(1, min(pagina, max(1, total_paginas)))
    offset = (pagina - 1) * projetos_por_pagina
    
    projetos_lista = query.offset(offset).limit(projetos_por_pagina).all()

    usuario_curtidas = set()
    if current_user.is_authenticated:
        curtidas = Curtida.query.filter_by(usuario_id=current_user.id).all()
        usuario_curtidas = set(c.projeto_id for c in curtidas)
    
    for projeto in projetos_lista:
        projeto.user_liked = projeto.id in usuario_curtidas
    
    cursos = [p.curso for p in Projeto.query.distinct(Projeto.curso).all() if p.curso]
    tipos = [p.tipo for p in Projeto.query.distinct(Projeto.tipo).all() if p.tipo]
    
    return render_template(
        'projetos.html',
        projetos=projetos_lista,
        cursos=cursos,
        tipos=tipos,
        curso_filtro=curso_filtro,
        tipo_filtro=tipo_filtro,
        ordenacao=ordenacao,
        q=q,
        pagina=pagina,
        total_paginas=total_paginas,
        total_projetos=total_projetos
    )


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
        tipo_usuario = 'Visitante'

        if senha != confirm:
            flash("As senhas não coincidem.", "error")
            return redirect(url_for('register'))

        if Usuario.query.filter_by(email=email).first():
            flash("Este email já está cadastrado.", "error")
            return redirect(url_for('register'))

        senha_hash = bcrypt.generate_password_hash(senha).decode('utf-8')
        novo_usuario = Usuario(nome=nome, email=email, senha=senha_hash, tipo_usuario=tipo_usuario) 
        db.session.add(novo_usuario)
        db.session.commit()

        flash('Cadastro realizado com sucesso! Agora faça login.', 'success')
        return redirect(url_for('login'))

    return render_template('register.html')

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
    imagens = []
    if getattr(projeto, 'estrutura', None):
        imagens = [p for p in projeto.estrutura.split(',') if p]

    imagens_urls = []
    for img in imagens:
        try:
            imagens_urls.append(url_for('static', filename=img))
        except Exception:
            continue

    comentarios_relativos = {}
    now = datetime.utcnow()
    for c in comentarios:
        if getattr(c, 'criado_em', None):
            diff = now - c.criado_em
            diff_seconds = int(diff.total_seconds())
            if diff_seconds < 60:
                rel = 'agora'
            elif diff_seconds < 3600:
                mins = diff_seconds // 60
                rel = f"há {mins} minuto{'s' if mins > 1 else ''}"
            elif diff_seconds < 86400:
                hrs = diff_seconds // 3600
                rel = f"há {hrs} hora{'s' if hrs > 1 else ''}"
            elif diff_seconds < 604800:
                days = diff_seconds // 86400
                rel = f"há {days} dia{'s' if days > 1 else ''}"
            else:
                rel = c.criado_em.strftime('%d/%m/%Y %H:%M')
        else:
            rel = 'data indisponível'
        comentarios_relativos[c.id] = rel

    return render_template(
        'listar_projeto.html', 
        projeto=projeto, 
        comentarios=comentarios, 
        comentarios_relativos=comentarios_relativos,
        liked=liked,
        heart_liked_exists=heart_liked_exists,
        heart_exists=heart_exists,
        heart_hover_exists=heart_hover_exists,
        imagens=imagens_urls
    )

@app.route("/projetoscurtidos")
@login_required
def projetos_curtidos():
    projetos = Projeto.query.join(Curtida, Curtida.projeto_id == Projeto.id).filter(Curtida.usuario_id == current_user.id).all()
    return render_template("projetos_curtidos.html", projetos=projetos)

@app.route("/login_suap")
def login_suap():
    
    params = {
        "response_type": "code",
        "client_id": SUAP_CLIENT_ID,
        "redirect_uri": SUAP_REDIRECT_URI,
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
        return redirect(url_for("login"))

    user_info = response.json()

    email = user_info.get("email")
    nome = user_info.get("nome_usual") or user_info.get("nome")
    vinculo = user_info.get("vinculo", {})

    suap_usuario = Usuario.query.filter_by(email=email).first()

    if not suap_usuario:
        suap_usuario = Usuario(
            nome=nome,
            email=email,
            senha=bcrypt.generate_password_hash("suap_login_default_123").decode("utf-8"),
            data_nascimento=user_info.get("data_nascimento"),
            cpf=user_info.get("cpf"),
            tipo_usuario=user_info.get("tipo_vinculo"),
            matricula=user_info.get("matricula"),
            curso=vinculo.get("curso"),
            campus=vinculo.get("campus"),
            foto=user_info.get("url_foto_150x200")
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
    return redirect(url_for("index"))

@app.route('/logout')
@login_required
def logout():   
    
    logout_user()
    flash('Logout realizado com sucesso!', 'success')
    return redirect(url_for('index'))

@app.route('/criarprojeto', methods=['GET','POST'], endpoint='criar_projeto')
@suap_required

@app.route('/editarprojeto/<int:id>', methods=['GET','POST'], endpoint='editar_projeto')
@suap_required
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

        try:
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
                _, _, pasta_pdfs, nome_pasta = criar_pastas_projeto(titulo)

                nome_pdf = secure_filename(arquivo.filename)
                caminho_pdf = os.path.join(pasta_pdfs, nome_pdf)
                arquivo.save(caminho_pdf)

                projeto.arquivo = f"uploads/projetos/{nome_pasta}/pdfs/{nome_pdf}"
            
            imagens = request.files.getlist('imagens[]')
        
            if projeto and projeto.estrutura:
                lista_imagens = [img for img in projeto.estrutura.split(',') if img.strip()]
            else:
                lista_imagens = []
                
            novas_imagens = [img for img in imagens if img and img.filename]
            
            if novas_imagens:
                _, pasta_imagens, _, nome_pasta = criar_pastas_projeto(titulo)

                for img in novas_imagens:
                    nome_img = secure_filename(img.filename)
                    caminho_img = os.path.join(pasta_imagens, nome_img)
                    img.save(caminho_img)

                    lista_imagens.append(
                        f"uploads/projetos/{nome_pasta}/imagens/{nome_img}"
                    )
                        
            if lista_imagens:
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
                    db.session.add(Link(url=link, projeto_id=projeto.id))

            links_extras = request.form.getlist('links[]')
            for link in links_extras:
                if link.strip():
                    db.session.add(Link(url=link, projeto_id=projeto.id))

            db.session.commit()
            
            msg = 'Projeto atualizado com sucesso!' if is_edit else 'Projeto cadastrado com sucesso!'
            flash(msg, 'success')
            return redirect(url_for('ver_projeto', id=projeto.id))
        
        except Exception as e:
            db.session.rollback()
            flash(f'Erro ao salvar projeto: {str(e)}', 'error')
            return redirect(request.url)

    link_principal_val = ''
    links_extras_val = ['']
    if projeto:
        principal = next((l.url for l in projeto.links if getattr(l, 'tipo', None) == 'principal'), None)
        if principal is None:
            if projeto.links:
                principal = projeto.links[0].url
        link_principal_val = principal or ''
        extras = [l.url for l in projeto.links if getattr(l, 'tipo', None) == 'extra']
        if not extras:
            extras = [l.url for l in projeto.links if l.url != link_principal_val]
        links_extras_val = extras if extras else ['']

    dados_projeto = {
        'titulo': projeto.titulo if projeto else '',
        'subtitulo': projeto.subtitulo if projeto else '',
        'descricao': projeto.descricao if projeto else '',
        'tipo': projeto.tipo if projeto else '',
        'curso': projeto.curso if projeto else '',
        'arquivo_nome': projeto.arquivo if projeto else '',
        
        'imagens': (projeto.estrutura.split(',') if projeto and projeto.estrutura else []) + [''] * (4 - len(projeto.estrutura.split(',') if projeto and projeto.estrutura else [])),
        'autores': projeto.autores if projeto and projeto.autores else [Autor(nome='', matricula='', tipo='')],
        'objetivos': projeto.objetivos if projeto and projeto.objetivos else [Objetivo(descricao=''), Objetivo(descricao=''), Objetivo(descricao='')],
        'metodologias': projeto.metodologias if projeto and projeto.metodologias else [Metodologia(descricao=''), Metodologia(descricao=''), Metodologia(descricao='')],
        'link_principal': link_principal_val,
        'links_extras': links_extras_val,

        'action_url': url_for('editar_projeto', id=id) if id else url_for('criar_projeto'),
        'submit_text': 'Atualizar Projeto' if id else 'Cadastrar Projeto',
        'header_title': 'Editar Projeto' if id else 'Cadastrar Novo Projeto',
        'header_subtitle': 'Altere os dados abaixo para atualizar seu projeto.' if id else 'Preencha os dados abaixo para publicar seu projeto na vitrine do IF.'
    }

    return render_template('criar_projeto.html', **dados_projeto)

@app.route('/projeto/<int:id>/excluir', methods=['POST'])
@suap_required
def excluir_projeto(id):
    
    projeto = Projeto.query.get_or_404(id)
    if projeto.usuario_id != current_user.id:
        flash('Você não tem permissão para excluir este projeto.', 'error')
        return redirect(url_for('meus_projetos'))
    
    try:
        try:
            nome_pasta = secure_filename(projeto.titulo.lower().replace(" ", "-"))
            pasta_projeto = os.path.join(BASE_DIR, "static", "uploads", "projetos", nome_pasta)
            if os.path.exists(pasta_projeto):
                shutil.rmtree(pasta_projeto)
        except Exception as fs_err:
            flash(f"Aviso: falha ao remover arquivos do projeto: {fs_err}", 'error')

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
    except Exception as e:
        db.session.rollback()
        flash(f'Erro ao excluir projeto: {str(e)}', 'error')
        return redirect(url_for('meus_projetos'))


@app.route('/meus_projetos')
@login_required
def meus_projetos():
    
    projetos = Projeto.query.filter_by(usuario_id=current_user.id).all()
    return render_template('meus_projetos.html', projetos=projetos)


@app.route('/projeto/<int:id>/comentario', methods=['POST'])
@login_required
def adicionar_comentario(id):
    
    projeto = Projeto.query.get_or_404(id)
    conteudo = request.form.get('conteudo')

    if not conteudo or not conteudo.strip():
        flash('Comentário vazio. Escreva algo antes de enviar.', 'error')
        return redirect(url_for('ver_projeto', id=id))

    comentario = Comentario(conteudo=conteudo.strip(), usuario_id=current_user.id, projeto_id=projeto.id)
    try:
        db.session.add(comentario)
        db.session.commit()
        flash('Comentário adicionado com sucesso!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Erro ao adicionar comentário: {str(e)}', 'error')

    return redirect(url_for('ver_projeto', id=id))


@app.route('/projeto/<int:id>/curtir', methods=['POST'])
@login_required
def curtir_projeto(id):
    
    projeto = Projeto.query.get_or_404(id)
    curtida = Curtida.query.filter_by(usuario_id=current_user.id, projeto_id=id).first()
    
    try:
        if curtida:
            db.session.delete(curtida)
            projeto.curtidas = max((projeto.curtidas or 0) - 1, 0)
            db.session.commit()
            return jsonify({'liked': False, 'curtidas': projeto.curtidas}), 200
        else:
            nova_curtida = Curtida(usuario_id=current_user.id, projeto_id=id)
            projeto.curtidas = (projeto.curtidas or 0) + 1
            db.session.add(nova_curtida)
            db.session.commit()
            return jsonify({'liked': True, 'curtidas': projeto.curtidas}), 200
            
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@app.route('/meu_perfil')
@login_required
def meu_perfil():
    
    return render_template('perfil.html', perfil=current_user)

@app.route("/alterar_foto", methods=["POST"])
@login_required
def alterar_foto():
    foto = request.files.get("foto")

    if not foto:
        flash("Nenhuma imagem enviada.", "error")
        return redirect(url_for("perfil"))

    caminho = f"static/uploads/users/{current_user.id}.jpg"
    foto.save(caminho)

    current_user.foto = "/" + caminho
    db.session.commit()

    flash("Foto atualizada com sucesso!", "success")
    return redirect(url_for("meu_perfil"))

@app.route("/perfil/<int:id>")
@login_required
def ver_perfil(id):
    
    perfil = Usuario.query.get(id)
    if perfil:
        return render_template("perfil.html", perfil=perfil)
    else:
        flash('Usuário não encontrado', 'error')
        return redirect (url_for('index'))

@app.route("/sobre")
def sobre():
    return render_template("sobre.html")

if __name__ == '__main__':
    app.run(debug=True)
