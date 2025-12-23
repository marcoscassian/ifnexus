
#criar, editar, e excluir projetos
from flask import request, redirect, url_for, flash, render_template
from flask_login import current_user
from werkzeug.utils import secure_filename
import os
import shutil

from . import projetos_bp
from extensions import db

from utils.files import criar_pastas_projeto
from utils.paths import BASE_DIR
from utils.decorator import suap_required

from models import Projeto, Autor, Objetivo, Metodologia, Link, Comentario, Curtida

@projetos_bp.route('/criarprojeto', methods=['GET','POST'], endpoint='criar_projeto')
@suap_required

@projetos_bp.route('/editarprojeto/<int:id>', methods=['GET','POST'], endpoint='editar_projeto')
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


            autores_ids = request.form.getlist('autores_ids[]')
            print("AUTORES:", autores_ids)

            for usuario_id in autores_ids:
                autor = Autor(
                    usuario_id=int(usuario_id),
                    projeto_id=projeto.id
                )
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
            return redirect(url_for('projetos.ver_projeto', id=projeto.id))

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
        'autores': projeto.autores if projeto and projeto.autores else [],
        'objetivos': projeto.objetivos if projeto and projeto.objetivos else [Objetivo(descricao=''), Objetivo(descricao=''), Objetivo(descricao='')],
        'metodologias': projeto.metodologias if projeto and projeto.metodologias else [Metodologia(descricao=''), Metodologia(descricao=''), Metodologia(descricao='')],
        'link_principal': link_principal_val,
        'links_extras': links_extras_val,

        'action_url': url_for('projetos.editar_projeto', id=id) if id else url_for('projetos.criar_projeto'),
        'submit_text': 'Atualizar Projeto' if id else 'Cadastrar Projeto',
        'header_title': 'Editar Projeto' if id else 'Cadastrar Novo Projeto',
        'header_subtitle': 'Altere os dados abaixo para atualizar seu projeto.' if id else 'Preencha os dados abaixo para publicar seu projeto na vitrine do IF.'
    }

    return render_template('projetos/criar_projeto.html', **dados_projeto)

@projetos_bp.route('/projeto/<int:id>/excluir', methods=['POST'])
@suap_required
def excluir_projeto(id):
    
    projeto = Projeto.query.get_or_404(id)
    if projeto.usuario_id != current_user.id:
        flash('Você não tem permissão para excluir este projeto.', 'error')
        return redirect(url_for('usuarios.meus_projetos'))
    
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
        return redirect(url_for('usuarios.meus_projetos'))
    except Exception as e:
        db.session.rollback()
        flash(f'Erro ao excluir projeto: {str(e)}', 'error')
        return redirect(url_for('usuarios.meus_projetos'))