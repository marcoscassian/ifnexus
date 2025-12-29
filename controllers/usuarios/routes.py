from flask import render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from sqlalchemy import or_

from extensions import db
from models import Projeto, Curtida, Usuario, Autor

from . import usuarios_bp

@usuarios_bp.route("/projetoscurtidos")
@login_required
def projetos_curtidos():
    projetos = Projeto.query.join(Curtida, Curtida.projeto_id == Projeto.id).filter(Curtida.usuario_id == current_user.id).all()
    return render_template("usuario/projetos_curtidos.html", projetos=projetos)

@usuarios_bp.route('/meus_projetos')
@login_required
def meus_projetos():

    projetos = Projeto.query\
        .outerjoin(Autor, Projeto.id == Autor.projeto_id)\
        .filter(
            or_(
                Projeto.usuario_id == current_user.id,  # é o dono
                Autor.usuario_id == current_user.id     # é coautor
            )
        ).distinct().all()
    return render_template('usuario/meus_projetos.html', projetos=projetos)

@usuarios_bp.route('/meu_perfil')
@login_required
def meu_perfil():
    
    return render_template('usuario/perfil.html', perfil=current_user)

@usuarios_bp.route("/alterar_foto", methods=["POST"])
@login_required
def alterar_foto():
    foto = request.files.get("foto")

    if not foto:
        flash("Nenhuma imagem enviada.", "error")
        return redirect(url_for("usuarios.perfil"))

    caminho = f"static/uploads/users/{current_user.id}.jpg"
    foto.save(caminho)

    current_user.foto = "/" + caminho
    db.session.commit()

    flash("Foto atualizada com sucesso!", "success")
    return redirect(url_for("usuarios.meu_perfil"))

@usuarios_bp.route("/perfil/<int:id>")
@login_required
def ver_perfil(id):
    
    perfil = Usuario.query.get(id)
    if perfil:
        return render_template("usuario/perfil.html", perfil=perfil)
    else:
        flash('Usuário não encontrado', 'error')
        return redirect (url_for('index'))