#funcoes auxiliares

from flask import jsonify, request
from . import projetos_bp

from utils.decorator import suap_required

from models import Usuario

@projetos_bp.route("/livesearch/usuarios")
@suap_required
def livesearch_usuarios():
    q = request.args.get("q", "").strip()

    if len(q) < 1:
        return jsonify([])

    usuarios = Usuario.query.filter(
        Usuario.nome.ilike(f"%{q}%")
    ).limit(8).all()

    return jsonify([
        {
            "id": u.id,
            "nome": u.nome,
            "matricula": u.matricula
        } for u in usuarios
    ])