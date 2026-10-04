import os
import shutil
from pathlib import Path
from urllib.parse import urlparse
from uuid import uuid4

from flask import flash, redirect, render_template, request, url_for
from flask_login import current_user
from werkzeug.utils import secure_filename

from extensions import db
from models import (
    Autor, Comentario, Curtida, Link, Metodologia, Objetivo, Projeto,
    ProjetoArquivo, ProjetoImagem, Tecnologia, Usuario,
)
from utils.decorator import suap_required
from utils.paths import PROJETOS_DIR, STATIC_DIR

from . import projetos_bp


TIPOS_PROJETO = {
    'projeto-integrador': 'Projeto Integrador', 'pesquisa': 'Pesquisa',
    'extensao': 'Extensão', 'ensino': 'Ensino', 'tcc': 'TCC',
    'pessoal': 'Projeto Pessoal', 'outro': 'Outro',
}
STATUS_PROJETO = {
    'ideia': 'Ideia', 'desenvolvimento': 'Em desenvolvimento',
    'testes': 'Em testes', 'concluido': 'Concluído',
}
CURSOS = {
    'informatica': 'Informática', 'textil': 'Têxtil',
    'vestuario': 'Vestuário', 'eletro': 'Eletrotécnica',
}
TIPOS_LINK = {'github', 'demonstracao', 'video', 'site', 'outro'}
IMAGE_EXTENSIONS = {'jpg', 'jpeg', 'png', 'webp'}
DOCUMENT_EXTENSIONS = {'pdf', 'doc', 'docx', 'ppt', 'pptx', 'odt', 'odp'}
MAX_IMAGE_SIZE = 8 * 1024 * 1024
MAX_DOCUMENT_SIZE = 10 * 1024 * 1024


def _clean_list(name):
    return [value.strip() for value in request.form.getlist(name) if value.strip()]


def _valid_url(value):
    parsed = urlparse(value)
    return parsed.scheme in {'http', 'https'} and bool(parsed.netloc)


def _file_size(storage):
    position = storage.stream.tell()
    storage.stream.seek(0, os.SEEK_END)
    size = storage.stream.tell()
    storage.stream.seek(position)
    return size


def _valid_image_signature(storage, extension):
    position = storage.stream.tell()
    header = storage.stream.read(16)
    storage.stream.seek(position)
    if extension in {'jpg', 'jpeg'}:
        return header.startswith(b'\xff\xd8\xff')
    if extension == 'png':
        return header.startswith(b'\x89PNG\r\n\x1a\n')
    if extension == 'webp':
        return header.startswith(b'RIFF') and header[8:12] == b'WEBP'
    return False


def _valid_document_signature(storage, extension):
    position = storage.stream.tell()
    header = storage.stream.read(8)
    storage.stream.seek(position)
    if extension == 'pdf':
        return header.startswith(b'%PDF-')
    if extension in {'docx', 'pptx', 'odt', 'odp'}:
        return header.startswith(b'PK\x03\x04')
    if extension in {'doc', 'ppt'}:
        return header.startswith(b'\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1')
    return False


def _validate_submission(publishing):
    errors = {}
    titulo = request.form.get('titulo', '').strip()
    descricao = request.form.get('descricao', '').strip()
    autores = [value for value in request.form.getlist('autores_ids[]') if value.isdigit()]

    if publishing:
        if not titulo:
            errors['titulo'] = 'Informe o título do projeto.'
        if not descricao:
            errors['descricao'] = 'Escreva um resumo ou descrição.'
        if request.form.get('tipo') not in TIPOS_PROJETO:
            errors['tipo'] = 'Selecione um tipo de projeto.'
        if request.form.get('curso') not in CURSOS:
            errors['curso'] = 'Selecione o curso.'
        if not _selected_users(autores):
            errors['autores'] = 'Adicione pelo menos um autor.'
        if not _clean_list('objetivos[]'):
            errors['objetivos'] = 'Adicione pelo menos um objetivo.'
        if not _clean_list('metodologias[]'):
            errors['metodologias'] = 'Adicione pelo menos uma etapa da metodologia.'

    if len(titulo) > 120:
        errors['titulo'] = 'Use no máximo 120 caracteres.'
    if len(request.form.get('subtitulo', '').strip()) > 150:
        errors['subtitulo'] = 'Use no máximo 150 caracteres.'
    if len(descricao) > 2000:
        errors['descricao'] = 'Use no máximo 2.000 caracteres.'
    if len(request.form.get('resultados', '').strip()) > 1200:
        errors['resultados'] = 'Use no máximo 1.200 caracteres.'
    if request.form.get('status', 'ideia') not in STATUS_PROJETO:
        errors['status'] = 'Selecione um status válido.'
    orientador_id = request.form.get('orientador_id', '')
    if orientador_id:
        orientador = db.session.get(Usuario, int(orientador_id)) if orientador_id.isdigit() else None
        if not orientador or (orientador.tipo_usuario or '').lower() not in {'docente', 'professor'}:
            errors['orientador'] = 'Selecione um professor ou docente cadastrado.'

    for index, url in enumerate(request.form.getlist('links_urls[]')):
        if url.strip() and not _valid_url(url.strip()):
            errors[f'link_{index}'] = 'Informe uma URL completa iniciada por http:// ou https://.'

    for image in request.files.getlist('imagens[]'):
        if not image or not image.filename:
            continue
        filename = secure_filename(image.filename)
        extension = filename.rsplit('.', 1)[-1].lower() if '.' in filename else ''
        if extension not in IMAGE_EXTENSIONS or not _valid_image_signature(image, extension):
            errors['imagens'] = 'Envie apenas imagens JPG, PNG ou WEBP válidas.'
            break
        if _file_size(image) > MAX_IMAGE_SIZE:
            errors['imagens'] = 'Cada imagem pode ter no máximo 8 MB.'
            break

    for document in request.files.getlist('arquivos[]'):
        if not document or not document.filename:
            continue
        filename = secure_filename(document.filename)
        extension = filename.rsplit('.', 1)[-1].lower() if '.' in filename else ''
        if extension not in DOCUMENT_EXTENSIONS or not _valid_document_signature(document, extension):
            errors['arquivos'] = 'Formato não permitido. Use PDF, DOC, DOCX, PPT, PPTX, ODT ou ODP.'
            break
        if _file_size(document) > MAX_DOCUMENT_SIZE:
            errors['arquivos'] = 'Cada documento pode ter no máximo 10 MB.'
            break
    return errors


def _selected_users(ids):
    numeric_ids = [int(value) for value in ids if str(value).isdigit()]
    if not numeric_ids:
        return []
    users = Usuario.query.filter(Usuario.id.in_(numeric_ids)).all()
    by_id = {user.id: user for user in users}
    return [by_id[user_id] for user_id in numeric_ids if user_id in by_id]


def _form_context(projeto=None, errors=None):
    if request.method == 'POST':
        autor_ids = request.form.getlist('autores_ids[]')
        autor_roles = request.form.getlist('autores_tipos[]')
        users = _selected_users(autor_ids)
        roles_by_id = {
            int(uid): (autor_roles[index] if index < len(autor_roles) else 'coautor')
            for index, uid in enumerate(autor_ids) if uid.isdigit()
        }
        autores = [{'usuario': user, 'tipo': roles_by_id.get(user.id, 'coautor')} for user in users]
        orientador = Usuario.query.get(request.form.get('orientador_id')) if request.form.get('orientador_id', '').isdigit() else None
        links = [
            {'tipo': tipo if tipo in TIPOS_LINK else 'outro', 'url': url}
            for tipo, url in zip(request.form.getlist('links_tipos[]'), request.form.getlist('links_urls[]'))
            if url.strip()
        ]
        context = {
            'titulo': request.form.get('titulo', ''), 'subtitulo': request.form.get('subtitulo', ''),
            'descricao': request.form.get('descricao', ''), 'tipo': request.form.get('tipo', ''),
            'curso': request.form.get('curso', ''), 'status': request.form.get('status', 'ideia'),
            'resultados': request.form.get('resultados', ''), 'autores': autores,
            'orientador': orientador, 'objetivos': _clean_list('objetivos[]'),
            'metodologias': _clean_list('metodologias[]'), 'links': links,
            'tecnologias': _clean_list('tecnologias[]'),
        }
    else:
        if projeto:
            project_authors = [
                {'usuario': item.usuario, 'tipo': item.tipo or 'coautor'}
                for item in projeto.autores if item.usuario
            ]
            if not any(item['usuario'].id == projeto.usuario_id for item in project_authors):
                project_authors.insert(0, {'usuario': projeto.dono, 'tipo': 'principal'})
            if project_authors and not any(item['tipo'] == 'principal' for item in project_authors):
                project_authors[0]['tipo'] = 'principal'
        else:
            project_authors = [{'usuario': current_user, 'tipo': 'principal'}]
        context = {
            'titulo': projeto.titulo if projeto else '', 'subtitulo': projeto.subtitulo if projeto else '',
            'descricao': projeto.descricao if projeto else '', 'tipo': projeto.tipo if projeto else '',
            'curso': projeto.curso if projeto else '', 'status': projeto.status if projeto else 'ideia',
            'resultados': projeto.resultados if projeto else '',
            'autores': project_authors,
            'orientador': projeto.orientador if projeto else None,
            'objetivos': [item.descricao for item in projeto.objetivos] if projeto else [''],
            'metodologias': [item.descricao for item in projeto.metodologias] if projeto else [''],
            'links': projeto.links if projeto else [],
            'tecnologias': [item.nome for item in projeto.tecnologias] if projeto else [],
        }

    context.update({
        'projeto': projeto, 'imagens_existentes': projeto.imagens if projeto else [],
        'arquivos_existentes': projeto.arquivos if projeto else [], 'errors': errors or {},
        'tipos_projeto': TIPOS_PROJETO, 'status_projeto': STATUS_PROJETO, 'cursos': CURSOS,
        'action_url': url_for('projetos.editar_projeto', id=projeto.id) if projeto else url_for('projetos.criar_projeto'),
        'header_title': 'Editar projeto' if projeto else 'Cadastrar novo projeto',
        'header_subtitle': 'Atualize as informações e publique quando estiver pronto.' if projeto else 'Compartilhe seu projeto com a comunidade do IFRN.',
    })
    return context


def _save_upload(storage, directory, allowed_extensions):
    original_name = secure_filename(storage.filename)
    extension = original_name.rsplit('.', 1)[-1].lower()
    if extension not in allowed_extensions:
        raise ValueError('Extensão de arquivo não permitida.')
    directory.mkdir(parents=True, exist_ok=True)
    destination = directory / f'{uuid4().hex}.{extension}'
    storage.save(destination)
    return destination.relative_to(Path(STATIC_DIR)).as_posix(), original_name, extension, destination.stat().st_size


def _safe_remove(relative_path):
    if not relative_path:
        return
    static_root = Path(STATIC_DIR).resolve()
    target = (static_root / relative_path).resolve()
    if static_root in target.parents and target.is_file():
        try:
            target.unlink()
        except OSError:
            pass


@projetos_bp.route('/criarprojeto', methods=['GET', 'POST'], endpoint='criar_projeto')
@projetos_bp.route('/editarprojeto/<int:id>', methods=['GET', 'POST'], endpoint='editar_projeto')
@suap_required
def gerenciar_projeto(id=None):
    projeto = Projeto.query.get_or_404(id) if id else None
    if projeto:
        pode_editar = projeto.usuario_id == current_user.id or any(autor.usuario_id == current_user.id for autor in projeto.autores)
        if not pode_editar:
            flash('Você não tem permissão para editar este projeto.', 'error')
            return redirect(url_for('usuarios.meus_projetos'))

    if request.method == 'GET':
        return render_template('projetos/criar_projeto.html', **_form_context(projeto))

    publishing = request.form.get('submit_action') == 'publish'
    errors = _validate_submission(publishing)
    if errors:
        return render_template('projetos/criar_projeto.html', **_form_context(projeto, errors)), 422

    is_edit = projeto is not None
    files_to_remove, new_files = [], []
    try:
        if not projeto:
            projeto = Projeto(usuario_id=current_user.id, titulo='Projeto sem título', descricao='')
            db.session.add(projeto)
            db.session.flush()

        projeto.titulo = request.form.get('titulo', '').strip() or 'Projeto sem título'
        projeto.subtitulo = request.form.get('subtitulo', '').strip() or None
        projeto.descricao = request.form.get('descricao', '').strip()
        projeto.tipo = request.form.get('tipo') or None
        projeto.curso = request.form.get('curso') or None
        projeto.status = request.form.get('status', 'ideia')
        projeto.resultados = request.form.get('resultados', '').strip() or None
        projeto.publicado = publishing
        projeto.orientador_id = int(request.form['orientador_id']) if request.form.get('orientador_id', '').isdigit() else None

        Autor.query.filter_by(projeto_id=projeto.id).delete()
        autor_ids = request.form.getlist('autores_ids[]')
        autor_roles = request.form.getlist('autores_tipos[]')
        seen_authors = set()
        pending_authors = []
        for index, raw_id in enumerate(autor_ids):
            if not raw_id.isdigit() or int(raw_id) in seen_authors:
                continue
            user_id = int(raw_id)
            if not db.session.get(Usuario, user_id):
                continue
            role = autor_roles[index] if index < len(autor_roles) else 'coautor'
            pending_authors.append((user_id, role))
            seen_authors.add(user_id)
        principal_assigned = False
        for index, (user_id, role) in enumerate(pending_authors):
            is_principal = role == 'principal' and not principal_assigned
            if not principal_assigned and index == len(pending_authors) - 1:
                is_principal = True
            principal_assigned = principal_assigned or is_principal
            db.session.add(Autor(
                usuario_id=user_id,
                projeto_id=projeto.id,
                tipo='principal' if is_principal else 'coautor',
            ))

        Objetivo.query.filter_by(projeto_id=projeto.id).delete()
        for ordem, descricao in enumerate(_clean_list('objetivos[]')):
            db.session.add(Objetivo(descricao=descricao, ordem=ordem, projeto_id=projeto.id))
        Metodologia.query.filter_by(projeto_id=projeto.id).delete()
        for ordem, descricao in enumerate(_clean_list('metodologias[]')):
            db.session.add(Metodologia(descricao=descricao, ordem=ordem, projeto_id=projeto.id))

        Link.query.filter_by(projeto_id=projeto.id).delete()
        for ordem, (link_type, url) in enumerate(zip(request.form.getlist('links_tipos[]'), request.form.getlist('links_urls[]'))):
            url = url.strip()
            if url:
                db.session.add(Link(tipo=link_type if link_type in TIPOS_LINK else 'outro', url=url, ordem=ordem, projeto_id=projeto.id))

        projeto.tecnologias.clear()
        for nome in _clean_list('tecnologias[]'):
            normalized = nome[:80]
            tecnologia = Tecnologia.query.filter(db.func.lower(Tecnologia.nome) == normalized.lower()).first()
            if not tecnologia:
                tecnologia = Tecnologia(nome=normalized)
            if tecnologia not in projeto.tecnologias:
                projeto.tecnologias.append(tecnologia)

        retained_image_ids = {int(value) for value in request.form.getlist('existing_image_ids[]') if value.isdigit()}
        kept_images = []
        for image in list(projeto.imagens):
            if image.id not in retained_image_ids:
                files_to_remove.append(image.caminho)
                db.session.delete(image)
            else:
                kept_images.append(image)
        db.session.flush()

        upload_root = Path(PROJETOS_DIR) / str(projeto.id)
        uploaded_images = []
        image_base_order = len(kept_images)
        for ordem, image in enumerate(request.files.getlist('imagens[]')):
            if image and image.filename:
                caminho, nome, _, _ = _save_upload(image, upload_root / 'imagens', IMAGE_EXTENSIONS)
                new_files.append(caminho)
                record = ProjetoImagem(caminho=caminho, nome_original=nome, ordem=image_base_order + ordem, projeto_id=projeto.id)
                db.session.add(record)
                uploaded_images.append(record)
        db.session.flush()

        available_images = kept_images + uploaded_images
        for image in available_images:
            image.is_capa = False
        cover_existing = request.form.get('cover_existing_id', '')
        cover_new = request.form.get('cover_new_index', '')
        if cover_existing.isdigit():
            chosen = next((image for image in kept_images if image.id == int(cover_existing)), None)
            if chosen:
                chosen.is_capa = True
        elif cover_new.isdigit() and int(cover_new) < len(uploaded_images):
            uploaded_images[int(cover_new)].is_capa = True
        elif available_images:
            available_images[0].is_capa = True

        retained_file_ids = {int(value) for value in request.form.getlist('existing_file_ids[]') if value.isdigit()}
        kept_files = []
        for document in list(projeto.arquivos):
            if document.id not in retained_file_ids:
                files_to_remove.append(document.caminho)
                db.session.delete(document)
            else:
                kept_files.append(document)
        db.session.flush()

        file_base_order = len(kept_files)
        for ordem, document in enumerate(request.files.getlist('arquivos[]')):
            if document and document.filename:
                caminho, nome, extensao, tamanho = _save_upload(document, upload_root / 'documentos', DOCUMENT_EXTENSIONS)
                new_files.append(caminho)
                db.session.add(ProjetoArquivo(caminho=caminho, nome_original=nome, extensao=extensao, tamanho=tamanho, ordem=file_base_order + ordem, projeto_id=projeto.id))

        db.session.commit()
        for path in files_to_remove:
            _safe_remove(path)

        if publishing:
            flash('Projeto atualizado e publicado!' if is_edit else 'Projeto publicado com sucesso!', 'success')
            return redirect(url_for('projetos.ver_projeto', id=projeto.id))
        flash('Rascunho salvo. Você pode continuar quando quiser.', 'success')
        return redirect(url_for('usuarios.meus_projetos'))
    except Exception as exc:
        db.session.rollback()
        for path in new_files:
            _safe_remove(path)
        flash(f'Não foi possível salvar o projeto: {exc}', 'error')
        return render_template('projetos/criar_projeto.html', **_form_context(projeto)), 500


@projetos_bp.route('/projeto/<int:id>/excluir', methods=['POST'])
@suap_required
def excluir_projeto(id):
    projeto = Projeto.query.get_or_404(id)
    pode_excluir = projeto.usuario_id == current_user.id or any(autor.usuario_id == current_user.id for autor in projeto.autores)
    if not pode_excluir:
        flash('Você não tem permissão para excluir este projeto.', 'error')
        return redirect(url_for('usuarios.meus_projetos'))

    try:
        project_dir = (Path(PROJETOS_DIR) / str(projeto.id)).resolve()
        uploads_root = Path(PROJETOS_DIR).resolve()
        Curtida.query.filter_by(projeto_id=id).delete()
        db.session.delete(projeto)
        db.session.commit()
        if uploads_root in project_dir.parents and project_dir.is_dir():
            shutil.rmtree(project_dir)
        flash('Projeto excluído com sucesso!', 'success')
    except Exception as exc:
        db.session.rollback()
        flash(f'Erro ao excluir projeto: {exc}', 'error')
    return redirect(url_for('usuarios.meus_projetos'))
