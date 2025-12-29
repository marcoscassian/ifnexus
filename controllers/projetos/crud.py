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
    # ---------------------------------------------------------
    # 1. VERIFICAÇÃO DE PERMISSÃO (GET e POST)
    # ---------------------------------------------------------
    if id:
        projeto = Projeto.query.get_or_404(id)
        
        # Verifica se é dono
        e_dono = (projeto.usuario_id == current_user.id)
        
        # Verifica se é coautor
        # Importante: Usamos count() ou first() para verificar existência de forma eficiente
        e_coautor = db.session.query(Autor).filter_by(
            projeto_id=projeto.id, 
            usuario_id=current_user.id
        ).first() is not None
        
        # Se não for nem dono nem coautor, bloqueia
        if not e_dono and not e_coautor:
            flash('Você não tem permissão para editar este projeto.', 'error')
            # ATENÇÃO: Verifique se a rota 'usuarios.meus_projetos' existe. 
            # Se for no mesmo blueprint, talvez seja 'projetos.meus_projetos'.
            return redirect(url_for('usuarios.meus_projetos')) 

    # ---------------------------------------------------------
    # 2. PROCESSAMENTO DO FORMULÁRIO (POST)
    # ---------------------------------------------------------
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
                # CRIANDO NOVO PROJETO
                projeto = Projeto(
                    titulo=titulo, subtitulo=subtitulo, descricao=descricao,
                    tipo=tipo, curso=curso, usuario_id=current_user.id
                )
                db.session.add(projeto)
                db.session.flush() # Gera o ID do projeto para usar abaixo
            else:
                # EDITANDO PROJETO EXISTENTE
                projeto.titulo = titulo
                projeto.subtitulo = subtitulo
                projeto.descricao = descricao
                projeto.tipo = tipo
                projeto.curso = curso
                
                # Limpa relações antigas para recriar
                Objetivo.query.filter_by(projeto_id=projeto.id).delete()
                Metodologia.query.filter_by(projeto_id=projeto.id).delete()
                Link.query.filter_by(projeto_id=projeto.id).delete()
                
                # --- AQUI ESTAVA O PROBLEMA COMUM ---
                # Não deletamos os autores ainda. Vamos gerenciar a lista primeiro.
                Autor.query.filter_by(projeto_id=projeto.id).delete()

            # --- UPLOAD DE ARQUIVOS (PDF) ---
            arquivo = request.files.get('arquivo')
            if arquivo and arquivo.filename:
                _, _, pasta_pdfs, nome_pasta = criar_pastas_projeto(titulo)
                nome_pdf = secure_filename(arquivo.filename)
                caminho_pdf = os.path.join(pasta_pdfs, nome_pdf)
                arquivo.save(caminho_pdf)
                projeto.arquivo = f"uploads/projetos/{nome_pasta}/pdfs/{nome_pdf}"
            
            # --- UPLOAD DE IMAGENS ---
            imagens = request.files.getlist('imagens[]')
            lista_imagens = [img for img in (projeto.estrutura.split(',') if projeto and projeto.estrutura else []) if img.strip()]
            novas_imagens = [img for img in imagens if img and img.filename]
            
            if novas_imagens:
                _, pasta_imagens, _, nome_pasta = criar_pastas_projeto(titulo)
                for img in novas_imagens:
                    nome_img = secure_filename(img.filename)
                    caminho_img = os.path.join(pasta_imagens, nome_img)
                    img.save(caminho_img)
                    lista_imagens.append(f"uploads/projetos/{nome_pasta}/imagens/{nome_img}")
            
            if lista_imagens:
                projeto.estrutura = ",".join(lista_imagens)

            # ---------------------------------------------------------
            # 3. LÓGICA CRÍTICA DE AUTORES (CORREÇÃO)
            # ---------------------------------------------------------
            # Pega lista do formulário e converte para Inteiros
            raw_autores = request.form.getlist('autores_ids[]')
            novos_autores_ids = set()
            for uid in raw_autores:
                if uid:
                    novos_autores_ids.add(int(uid))

            # PROTEÇÃO: Se quem está editando NÃO é o dono (é um coautor),
            # precisamos garantir que ele não se exclua da lista, 
            # mesmo que o front-end não tenha enviado o ID dele.
            if projeto and (projeto.usuario_id != current_user.id):
                novos_autores_ids.add(current_user.id)

            # Re-adiciona os autores no banco
            for usuario_id in novos_autores_ids:
                # Nunca adicione o dono na tabela de autores (redundância)
                if usuario_id != projeto.usuario_id:
                    db.session.add(Autor(usuario_id=usuario_id, projeto_id=projeto.id))

            # --- DEMAIS CAMPOS (Objetivos, Metodologias, Links) ---
            for obj in request.form.getlist('objetivos[]'):
                if obj.strip(): db.session.add(Objetivo(descricao=obj, projeto_id=projeto.id))

            for met in request.form.getlist('metodologias[]'):
                if met.strip(): db.session.add(Metodologia(descricao=met, projeto_id=projeto.id))

            for link in request.form.getlist('links_principais[]'):
                if link.strip(): db.session.add(Link(url=link, projeto_id=projeto.id)) # add tipo='principal' se houver

            for link in request.form.getlist('links[]'):
                if link.strip(): db.session.add(Link(url=link, projeto_id=projeto.id)) # add tipo='extra' se houver

            db.session.commit()
            
            msg = 'Projeto atualizado!' if is_edit else 'Projeto cadastrado!'
            flash(msg, 'success')
            
            # Verifique se essa rota existe no seu blueprint 'projetos'
            return redirect(url_for('projetos.ver_projeto', id=projeto.id))

        except Exception as e:
            db.session.rollback()
            # O print ajuda a ver o erro no terminal do Flask
            print(f"ERRO AO SALVAR PROJETO: {e}") 
            flash(f'Erro ao salvar: {str(e)}', 'error')
            return redirect(request.url)

    # ---------------------------------------------------------
    # 4. PREPARAÇÃO DE DADOS PARA O TEMPLATE (GET)
    # ---------------------------------------------------------
    # (O restante do código permanece igual ao seu original, apenas organizando)
    link_principal_val = ''
    links_extras_val = ['']
    if projeto and projeto.links:
        # Lógica simples para separar links
        todos_links = [l.url for l in projeto.links]
        if todos_links:
            link_principal_val = todos_links[0]
            links_extras_val = todos_links[1:] if len(todos_links) > 1 else ['']

    dados_projeto = {
        'titulo': projeto.titulo if projeto else '',
        'subtitulo': projeto.subtitulo if projeto else '',
        'descricao': projeto.descricao if projeto else '',
        'tipo': projeto.tipo if projeto else '',
        'curso': projeto.curso if projeto else '',
        'arquivo_nome': projeto.arquivo if projeto else '',
        'imagens': (projeto.estrutura.split(',') if projeto and projeto.estrutura else []) + [''] * 4,
        'autores': projeto.autores if projeto and projeto.autores else [],
        'objetivos': projeto.objetivos if projeto and projeto.objetivos else [Objetivo(descricao='')]*3,
        'metodologias': projeto.metodologias if projeto and projeto.metodologias else [Metodologia(descricao='')]*3,
        'link_principal': link_principal_val,
        'links_extras': links_extras_val,
        'action_url': url_for('projetos.editar_projeto', id=id) if id else url_for('projetos.criar_projeto'),
        'submit_text': 'Atualizar Projeto' if id else 'Cadastrar Projeto',
        'header_title': 'Editar Projeto' if id else 'Cadastrar Novo Projeto',
        'header_subtitle': 'Altere os dados abaixo.' if id else 'Preencha os dados abaixo.'
    }
    # Ajusta tamanho das listas para o template não quebrar
    dados_projeto['imagens'] = dados_projeto['imagens'][:4]

    return render_template('projetos/criar_projeto.html', **dados_projeto)

@projetos_bp.route('/projeto/<int:id>/excluir', methods=['POST'])
@suap_required
def excluir_projeto(id):
    
    projeto = Projeto.query.get_or_404(id)
    
    e_dono = projeto.usuario_id == current_user.id
    e_coautor = Autor.query.filter_by(projeto_id=projeto.id, usuario_id=current_user.id).first() is not None
    
    if not e_dono and not e_coautor:
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