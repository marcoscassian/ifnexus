from flask import Flask, render_template, url_for, request, flash, redirect, jsonify
from flask_login import LoginManager, login_user, UserMixin, login_required, logout_user, current_user
from flask_bcrypt import Bcrypt
from werkzeug.utils import secure_filename
import os
import requests
from urllib.parse import urlencode

# --- Configurações SUAP ---
SUAP_CLIENT_ID = "G4IXTGHpxPafBmBGszCAuvxe6iBZgoK3W83HIUSE"
SUAP_REDIRECT_URI = "http://127.0.0.1:5000/callback_suap"
SUAP_AUTH_URL = "https://suap.ifrn.edu.br/o/authorize/"
SUAP_TOKEN_URL = "https://suap.ifrn.edu.br/o/token/"
SUAP_API_URL = "https://suap.ifrn.edu.br/api/v2/minhas-informacoes/meus-dados/"

# --- Importação dos Models (Necessário um arquivo models.py) ---
# Assumindo que 'models.py' está no mesmo diretório e define as classes:
# db, Usuario, Projeto, Autor, Objetivo, Metodologia, Link, Comentario, Curtida
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

# --- Configuração do Aplicativo Flask ---
app = Flask(__name__)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Configurações de Upload
app.config['UPLOAD_FOLDER_PDF'] = os.path.join(BASE_DIR, 'static', 'uploads', 'pdf')
app.config['UPLOAD_FOLDER_IMG'] = os.path.join(BASE_DIR, 'static', 'uploads', 'img')

ALLOWED_IMG_EXT = {'png', 'jpg', 'jpeg'}

os.makedirs(app.config['UPLOAD_FOLDER_PDF'], exist_ok=True)
os.makedirs(app.config['UPLOAD_FOLDER_IMG'], exist_ok=True)

# Configurações do SQLAlchemy e Secret Key
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///banco.db'
app.secret_key = 'ifnexus'

# Inicialização e Configuração de Extensões
db.init_app(app)
bcrypt = Bcrypt(app)

with app.app_context():
    db.create_all()

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"

@login_manager.user_loader
def load_user(user_id):
    """Função para carregar o usuário para o Flask-Login."""
    return Usuario.query.get(int(user_id))

# ----------------- Rotas Públicas -----------------

@app.route('/')
def index():
    """Rota da página inicial com cards de projetos de exemplo."""
    # Estes cards são estáticos, em uma aplicação real eles seriam buscados do banco de dados
    cards = [
        { "id": 1, "titulo": "IFNexus", "descricao": "O IFNexus é uma vitrine digital desenvolvida para divulgar e valorizar os projetos criados por estudantes e servidores do IFRN.", "imagem": "/static/img1.jpg", "tag": "Informática" },
        { "id": 2, "titulo": "SIMER", "descricao": "Sistema que monitora o consumo de energia em tempo real, identifica os maiores gastos e sugere formas de economizar.", "imagem": "/static/img2.jpg", "tag": "Eletrotécnica" },
        { "id": 3, "titulo": "EcoFios", "descricao": "Projeto voltado à produção de fios ecológicos reutilizando sobras de tecido. Busca reduzir o desperdício na indústria têxtil.", "imagem": "/static/img3.jpg", "tag": "Têxtil" },
        { "id": 4, "titulo": "Modus", "descricao": "Criação de roupas sustentáveis usando materiais ecológicos para reduzir o impacto ambiental da moda.", "imagem": "/static/img4.jpg", "tag": "Vestuário" },
    ]
    return render_template('index.html', cards=cards)

@app.route('/login', methods=['GET', 'POST'])
def login():
    """Rota para login de usuário local."""
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
    """Rota para registro de novo usuário local."""
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
        # Note: A senha não é mais um campo obrigatório para usuários SUAP, mas é para registro local.
        novo_usuario = Usuario(nome=nome, email=email, senha=senha_hash) 
        db.session.add(novo_usuario)
        db.session.commit()

        flash('Cadastro realizado com sucesso! Agora faça login.', 'success')
        return redirect(url_for('login'))

    return render_template('register.html')

@app.route('/projeto/<int:id>')
def ver_projeto(id):
    """Rota para visualização de um projeto específico."""
    projeto = Projeto.query.get_or_404(id)
    comentarios = Comentario.query.filter_by(projeto_id=id).order_by(Comentario.criado_em.desc()).all()
    
    liked = False
    if current_user.is_authenticated:
        liked = Curtida.query.filter_by(usuario_id=current_user.id, projeto_id=id).first() is not None

    # Verifica a existência dos arquivos de ícone de curtida para o template
    static_path = os.path.join(BASE_DIR, 'static', 'img', 'interacoes', 'curtidas')
    heart_liked_exists = os.path.exists(os.path.join(static_path, 'heartliked.png'))
    heart_exists = os.path.exists(os.path.join(static_path, 'heart.png'))
    heart_hover_exists = os.path.exists(os.path.join(static_path, 'hearthover.png'))

    return render_template(
        'listar_projeto.html', 
        projeto=projeto, 
        comentarios=comentarios, 
        liked=liked,
        heart_liked_exists=heart_liked_exists,
        heart_exists=heart_exists,
        heart_hover_exists=heart_hover_exists
    )

# ----------------- Rotas de Autenticação SUAP -----------------

@app.route("/login_suap")
def login_suap():
    """Redireciona para o portal de autorização do SUAP."""
    params = {
        "response_type": "code",
        "client_id": SUAP_CLIENT_ID,
        "redirect_uri": SUAP_REDIRECT_URI,
        "scope": "identificacao email", # Pede permissão para acessar identificação e email
    }

    return redirect(f"{SUAP_AUTH_URL}?{urlencode(params)}")

@app.route("/callback_suap")
def callback_suap():
    """Rota de callback do SUAP para processar o código de autorização."""
    code = request.args.get("code")
    if not code:
        flash("Erro: nenhum código recebido do SUAP.", "error")
        return redirect(url_for("login"))

    # 1. Trocar o código pelo Access Token
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

    # 2. Buscar dados do usuário com o Access Token
    headers = {"Authorization": f"Bearer {access_token}"}
    user_info = requests.get(SUAP_API_URL, headers=headers).json()

    print(user_info) # Log para depuração

    email = user_info.get("email")
    # Tenta usar o nome usual, senão usa o nome completo
    nome = user_info.get("nome_usual") or user_info.get("nome")

    # 3. Verificar/Criar usuário no banco de dados local
    usuario = Usuario.query.filter_by(email=email).first()
    vinculo = user_info.get("vinculo", {})

    if not usuario:
        # Criar um novo usuário no banco de dados
        usuario = Usuario(
            nome=nome,
            email=email,
            # Gera um hash para uma senha padrão/fake, pois o login será sempre via SUAP
            senha=bcrypt.generate_password_hash("suap_login_default_123").decode('utf-8'),
            data_nascimento = user_info.get("data_nascimento"),
            cpf = user_info.get("cpf"),
            tipo_usuario = user_info.get("tipo_vinculo"),
            matricula = user_info.get("matricula"),
            curso = vinculo.get("curso"),
            campus = vinculo.get("campus"),
            foto = user_info.get("url_foto_150x200")
        )
        db.session.add(usuario)
        db.session.commit()

    # 4. Logar o usuário
    login_user(usuario)
    flash("Login via SUAP realizado com sucesso!", "success")
    return redirect(url_for("index"))

# ----------------- Rotas Protegidas (Requer login) -----------------

@app.route('/logout')
@login_required
def logout():
    """Rota para logout de usuário."""
    logout_user()
    flash('Logout realizado com sucesso!', 'success')
    return redirect(url_for('index'))

@app.route('/criarprojeto', methods=['GET','POST'], endpoint='criar_projeto')
@app.route('/editarprojeto/<int:id>', methods=['GET','POST'], endpoint='editar_projeto')
@login_required
def gerenciar_projeto(id=None):
    """
    Rota unificada para criação (id=None) e edição (id presente) de projetos.
    Esta é a versão mais completa e será usada como a única rota de CRUD.
    """
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
                # Criar Novo Projeto
                projeto = Projeto(
                    titulo=titulo,
                    subtitulo=subtitulo,
                    descricao=descricao,
                    tipo=tipo,
                    curso=curso,
                    usuario_id=current_user.id
                )
                db.session.add(projeto)
                db.session.flush() # Necessário para obter o ID do novo projeto antes do commit

            else:
                # Atualizar Projeto Existente
                projeto.titulo = titulo
                projeto.subtitulo = subtitulo
                projeto.descricao = descricao
                projeto.tipo = tipo
                projeto.curso = curso
                
                # Limpar dados antigos associados antes de adicionar os novos
                Autor.query.filter_by(projeto_id=projeto.id).delete()
                Objetivo.query.filter_by(projeto_id=projeto.id).delete()
                Metodologia.query.filter_by(projeto_id=projeto.id).delete()
                Link.query.filter_by(projeto_id=projeto.id).delete()

            # --- Upload e Salvar Arquivo PDF ---
            arquivo = request.files.get('arquivo')
            if arquivo and arquivo.filename:
                nome_pdf = secure_filename(arquivo.filename)
                caminho_pdf = os.path.join(app.config['UPLOAD_FOLDER_PDF'], nome_pdf)
                arquivo.save(caminho_pdf)
                projeto.arquivo = nome_pdf
            
            # --- Upload e Salvar Imagens ---
            imagens = request.files.getlist('imagens[]')
            lista_imagens = []
            if any(img.filename for img in imagens):
                for img in imagens:
                    if img and img.filename:
                        nome_img = secure_filename(img.filename)
                        caminho_img = os.path.join(app.config['UPLOAD_FOLDER_IMG'], nome_img)
                        img.save(caminho_img)
                        lista_imagens.append(nome_img)
                # Salva os nomes dos arquivos separados por vírgula
                projeto.estrutura = ",".join(lista_imagens)

            # --- Adicionar Autores ---
            nomes_autores = request.form.getlist('autor_nome[]')
            matriculas_autores = request.form.getlist('autor_matricula[]')
            tipos_autores = request.form.getlist('autor_tipo[]')

            for nome, matricula, tipo in zip(nomes_autores, matriculas_autores, tipos_autores):
                if nome.strip() and matricula.strip() and tipo.strip():
                    autor = Autor(nome=nome, matricula=matricula, tipo=tipo, projeto_id=projeto.id)
                    db.session.add(autor)

            # --- Adicionar Objetivos ---
            objetivos = request.form.getlist('objetivos[]')
            for obj in objetivos:
                if obj.strip():
                    db.session.add(Objetivo(descricao=obj, projeto_id=projeto.id))

            # --- Adicionar Metodologias ---
            metodologias = request.form.getlist('metodologias[]')
            for met in metodologias:
                if met.strip():
                    db.session.add(Metodologia(descricao=met, projeto_id=projeto.id))

            # --- Adicionar Links ---
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
        
        except Exception as e:
            db.session.rollback()
            flash(f'Erro ao salvar projeto: {str(e)}', 'error')
            return redirect(request.url)


    # Lógica GET: Prepara os dados para o formulário
    
    # Preenchimento dinâmico para edição (se projeto existe) ou valores padrão (se é criação)
    dados_projeto = {
        'titulo': projeto.titulo if projeto else '',
        'subtitulo': projeto.subtitulo if projeto else '',
        'descricao': projeto.descricao if projeto else '',
        'tipo': projeto.tipo if projeto else '',
        'curso': projeto.curso if projeto else '',
        'arquivo_nome': projeto.arquivo if projeto else '',
        
        # Cria uma lista de 4 strings vazias ou preenche com as imagens existentes (para preencher 4 campos no form)
        'imagens': (projeto.estrutura.split(',') if projeto and projeto.estrutura else []) + [''] * (4 - len(projeto.estrutura.split(',') if projeto and projeto.estrutura else [])),
        
        # Autores: preenche com dados ou com 3 objetos Autor vazios para o formulário
        'autores': projeto.autores if projeto and projeto.autores else [Autor(nome='', matricula='', tipo=''), Autor(nome='', matricula='', tipo=''), Autor(nome='', matricula='', tipo='')],
        
        # Objetivos: preenche com dados ou com 3 objetos Objetivo vazios
        'objetivos': projeto.objetivos if projeto and projeto.objetivos else [Objetivo(descricao=''), Objetivo(descricao=''), Objetivo(descricao='')],
        
        # Metodologias: preenche com dados ou com 3 objetos Metodologia vazios
        'metodologias': projeto.metodologias if projeto and projeto.metodologias else [Metodologia(descricao=''), Metodologia(descricao=''), Metodologia(descricao='')],
        
        # Link Principal: busca o link do tipo 'principal' ou vazio
        'link_principal': next((link.url for link in projeto.links if link.tipo == 'principal'), '') if projeto else '',
        
        # Links Extras: busca links extras ou uma lista com uma string vazia (para 1 campo no form)
        'links_extras': [link.url for link in projeto.links if link.tipo == 'extra'] if projeto and any(link.tipo == 'extra' for link in projeto.links) else [''],

        'action_url': url_for('editar_projeto', id=id) if id else url_for('criar_projeto'),
        'submit_text': 'Atualizar Projeto' if id else 'Cadastrar Projeto',
        'header_title': 'Editar Projeto' if id else 'Cadastrar Novo Projeto',
        'header_subtitle': 'Altere os dados abaixo para atualizar seu projeto.' if id else 'Preencha os dados abaixo para publicar seu projeto na vitrine do IF.'
    }

    return render_template('criar_projeto.html', **dados_projeto)

@app.route('/projeto/<int:id>/excluir', methods=['POST'])
@login_required
def excluir_projeto(id):
    """Rota para exclusão de um projeto (e todos os dados relacionados)."""
    projeto = Projeto.query.get_or_404(id)
    if projeto.usuario_id != current_user.id:
        flash('Você não tem permissão para excluir este projeto.', 'error')
        return redirect(url_for('meus_projetos'))
    
    try:
        # Exclui todas as dependências do projeto
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
    """Exibe a lista de projetos criados pelo usuário logado."""
    projetos = Projeto.query.filter_by(usuario_id=current_user.id).all()
    return render_template('meus_projetos.html', projetos=projetos)


@app.route('/projeto/<int:id>/comentario', methods=['POST'])
@login_required
def adicionar_comentario(id):
    """Adiciona um comentário a um projeto."""
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
    """Curte ou descurte um projeto via AJAX/Fetch."""
    projeto = Projeto.query.get_or_404(id)
    curtida = Curtida.query.filter_by(usuario_id=current_user.id, projeto_id=id).first()
    
    try:
        if curtida:
            # Descurtir
            db.session.delete(curtida)
            projeto.curtidas = max((projeto.curtidas or 0) - 1, 0) # Garante que o contador não seja negativo
            db.session.commit()
            return jsonify({'liked': False, 'curtidas': projeto.curtidas}), 200
        else:
            # Curtir
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
    """Exibe o perfil do usuário logado."""
    return render_template('perfil.html', perfil=current_user)

@app.route("/perfil/<int:id>")
def ver_perfil(id):
    """Exibe o perfil de um usuário específico."""
    perfil = Usuario.query.get(id)
    if perfil:
        return render_template("perfil.html", perfil=perfil)
    else:
        flash('Usuário não encontrado', 'error')
        return redirect (url_for('index'))

@app.route("/projetoscurtidos")
@login_required
def projetos_curtidos():
    """Exibe os projetos curtidos pelo usuário logado."""
    # Nota: A implementação da busca no banco de dados para os projetos curtidos
    # dependerá da estrutura do seu model Curtida e da relação com Projeto.
    # Se Curtida.query.filter_by(usuario_id=current_user.id).all() retornar as curtidas,
    # você precisará acessar o projeto associado.
    
    # Exemplo de como obter os projetos (assumindo que Curtida tem uma relação 'projeto')
    curtidas = Curtida.query.filter_by(usuario_id=current_user.id).all()
    projetos = [curtida.projeto for curtida in curtidas] # Isso depende do seu modelo!
    
    # A rota original no seu código usava POST e não tinha lógica de busca. 
    # Mudei para GET e adicionei uma lógica de busca (dependente dos seus models).
    return render_template("projetos_curtidos.html", projetos=projetos)


# ----------------- Bloco de Execução Principal -----------------
if __name__ == '__main__':
    # Você deve garantir que 'models.py' esteja configurado corretamente 
    # e que os templates ('index.html', 'login.html', 'register.html', 
    # 'criar_projeto.html', 'listar_projeto.html', 'meus_projetos.html', 
    # 'perfil.html', 'projetos_curtidos.html') existam no diretório 'templates'.
    app.run(debug=True)
