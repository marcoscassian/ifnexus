#funcoes auxiliares

from flask import jsonify, request, flash
from . import projetos_bp
from extensions import db

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
