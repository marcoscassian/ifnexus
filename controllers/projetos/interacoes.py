#interações com projetos: comentários e curtidas
from flask import jsonify, request, flash, redirect, url_for
from flask_login import login_required, current_user
from . import projetos_bp

from extensions import db
from models import Projeto, Comentario, Curtida

@projetos_bp.route('/projeto/<int:id>/comentario', methods=['POST'])
@login_required
def adicionar_comentario(id):
    
    projeto = Projeto.query.get_or_404(id)
    conteudo = request.form.get('conteudo')

    if not conteudo or not conteudo.strip():
        flash('Comentário vazio. Escreva algo antes de enviar.', 'error')
        return redirect(url_for('projetos.ver_projeto', id=id))

    comentario = Comentario(conteudo=conteudo.strip(), usuario_id=current_user.id, projeto_id=projeto.id)
    try:
        db.session.add(comentario)
        db.session.commit()
        flash('Comentário adicionado com sucesso!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Erro ao adicionar comentário: {str(e)}', 'error')

    return redirect(url_for('projetos.ver_projeto', id=id))


@projetos_bp.route('/projeto/<int:id>/curtir', methods=['POST'])
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