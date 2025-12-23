#ver todos os projetos e exibir um projeto específico

from flask import render_template, request, url_for
from flask_login import current_user
from datetime import datetime

from utils.paths import BASE_DIR
from extensions import db
from models import Projeto
from . import projetos_bp
import os

from models import Comentario, Curtida, Autor

@projetos_bp.route('/projeto/<int:id>')
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
        'projetos/listar_projeto.html', 
        projeto=projeto, 
        comentarios=comentarios, 
        comentarios_relativos=comentarios_relativos,
        liked=liked,
        heart_liked_exists=heart_liked_exists,
        heart_exists=heart_exists,
        heart_hover_exists=heart_hover_exists,
        imagens=imagens_urls
    )


@projetos_bp.route('/projetos')
def projetos():
    curso_filtro = request.args.get('curso', '').strip()
    tipo_filtro = request.args.get('tipo', '').strip()
    ordenacao = request.args.get('ordenacao', 'curtidas').strip()
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
        'projetos/projetos.html',
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