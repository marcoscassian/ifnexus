from flask import render_template, flash
from models import Projeto
from . import main_bp

@main_bp.route('/')
def index():
    projetos_publicados = Projeto.query.filter(Projeto.publicado.is_(True))
    projetos_top = projetos_publicados.order_by(
        Projeto.curtidas.desc(),
        Projeto.id.desc(),
    ).limit(4).all()

    categorias = {
        'informatica': ['informatica', 'informática', 'info'],
        'eletro': ['eletro', 'eletrotecnica', 'eletrotécnica'],
        'textil': ['textil', 'têxtil'],
        'vestuario': ['vestuario', 'vestuário'],
    }
    projetos_top_por_categoria = {}
    for categoria, variacoes in categorias.items():
        encontrados = []
        vistos = set()
        for variacao in variacoes:
            candidatos = projetos_publicados.filter(
                Projeto.curso.ilike(f'%{variacao}%')
            ).order_by(
                Projeto.curtidas.desc(),
                Projeto.id.desc(),
            ).limit(4).all()
            for projeto in candidatos:
                if projeto.id not in vistos:
                    vistos.add(projeto.id)
                    encontrados.append(projeto)
            if len(encontrados) == 4:
                break
        projetos_top_por_categoria[categoria] = encontrados[:4]

    cards = []
    projetos_necessarios = list(projetos_top)
    seen_ids = {projeto.id for projeto in projetos_top}
    for projeto in [
        projeto
        for lista in projetos_top_por_categoria.values()
        for projeto in lista
    ]:
        if projeto.id not in seen_ids:
            seen_ids.add(projeto.id)
            projetos_necessarios.append(projeto)

    for projeto in projetos_necessarios:
        if projeto.curso:
            curso_normalizado = projeto.curso.strip().lower()
        else:
            curso_normalizado = ''
        categoria_projeto = next(
            (
                categoria
                for categoria, variacoes in categorias.items()
                if any(variacao in curso_normalizado for variacao in variacoes)
            ),
            curso_normalizado.replace(' ', '-'),
        )

        img_url = projeto.caminho_capa or "/static/img1.jpg"
        autores = [
            autor.usuario.nome
            for autor in projeto.autores
            if autor.usuario
        ]
        if projeto.dono:
            autores.append(projeto.dono.nome)

        cards.append({
            "id": projeto.id,
            "titulo": projeto.titulo,
            "descricao": projeto.descricao,
            "imagem": img_url,
            "tag": projeto.curso or "Sem curso",
            "tecnologias": [tecnologia.nome for tecnologia in projeto.tecnologias],
            "autores": list(dict.fromkeys(autores)),
            "general_top": projeto.id in {item.id for item in projetos_top},
            "course_top": projeto.id in {
                item.id
                for item in projetos_top_por_categoria.get(categoria_projeto, [])
            },
        })
    
    return render_template('index.html', cards=cards)

@main_bp.route("/sobre")
def sobre():
    return render_template("sobre.html")
