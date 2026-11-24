#funcoes auxiliares

from flask import jsonify, request, flash
from . import projetos_bp
from extensions import db

from utils.decorator import suap_required

from models import Usuario, Tecnologia

@projetos_bp.route("/livesearch/usuarios")
def livesearch_usuarios():
    q = request.args.get("q", "").strip()

    if len(q) < 1:
        return jsonify([])

    usuarios = Usuario.query.filter(
        Usuario.nome.ilike(f"%{q}%")
    )
    if request.args.get('tipo') == 'orientador':
        usuarios = usuarios.filter(
            db.func.lower(Usuario.tipo_usuario).in_(['docente', 'professor'])
        )
    usuarios = usuarios.limit(8).all()

    return jsonify([
        {
            "id": u.id,
            "nome": u.nome,
            "matricula": u.matricula,
            "tipo_usuario": u.tipo_usuario
        } for u in usuarios
    ])


@projetos_bp.route("/livesearch/tecnologias")
def livesearch_tecnologias():
    q = request.args.get("q", "").strip()
    if len(q) < 1:
        return jsonify([])

    tecnologias = (
        Tecnologia.query
        .filter(Tecnologia.nome.ilike(f"%{q}%"))
        .order_by(Tecnologia.nome.asc())
        .limit(10)
        .all()
    )
    return jsonify([{"nome": tecnologia.nome} for tecnologia in tecnologias])
