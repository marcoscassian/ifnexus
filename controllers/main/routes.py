from flask import render_template
from models import Projeto
from . import main_bp

@main_bp.route('/')
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

@main_bp.route("/sobre")
def sobre():
    return render_template("sobre.html")