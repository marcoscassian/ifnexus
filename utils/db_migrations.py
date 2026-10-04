"""Migrações pequenas e idempotentes para instalações existentes do IFNexus.

O projeto ainda não usa Alembic. Esta rotina preserva o banco atual e acrescenta
somente as colunas necessárias; tabelas novas são criadas pelo ``db.create_all``.
"""

from sqlalchemy import inspect, text

from extensions import db


def _columns(table_name):
    inspector = inspect(db.engine)
    if table_name not in inspector.get_table_names():
        return set()
    return {column['name'] for column in inspector.get_columns(table_name)}


def ensure_project_schema():
    statements = []

    projeto_columns = _columns('projetos')
    additions = {
        'status': "ALTER TABLE projetos ADD COLUMN status VARCHAR(30) NOT NULL DEFAULT 'ideia'",
        'publicado': 'ALTER TABLE projetos ADD COLUMN publicado BOOLEAN NOT NULL DEFAULT 1',
        'resultados': 'ALTER TABLE projetos ADD COLUMN resultados TEXT',
        'orientador_id': 'ALTER TABLE projetos ADD COLUMN orientador_id INTEGER',
    }
    statements.extend(sql for name, sql in additions.items() if name not in projeto_columns)

    for table_name in ('objetivos', 'metodologias'):
        if 'ordem' not in _columns(table_name):
            statements.append(f'ALTER TABLE {table_name} ADD COLUMN ordem INTEGER NOT NULL DEFAULT 0')

    link_columns = _columns('links')
    if 'tipo' not in link_columns:
        statements.append("ALTER TABLE links ADD COLUMN tipo VARCHAR(30) NOT NULL DEFAULT 'outro'")
    if 'ordem' not in link_columns:
        statements.append('ALTER TABLE links ADD COLUMN ordem INTEGER NOT NULL DEFAULT 0')

    autor_columns = _columns('autores')
    if 'tipo' not in autor_columns:
        statements.append("ALTER TABLE autores ADD COLUMN tipo VARCHAR(50) NOT NULL DEFAULT 'coautor'")

    if statements:
        with db.engine.begin() as connection:
            for statement in statements:
                connection.execute(text(statement))

    _migrate_legacy_authors()
    _migrate_legacy_uploads()


def _migrate_legacy_authors():
    tables = set(inspect(db.engine).get_table_names())
    if not {'projetos', 'autores'}.issubset(tables):
        return
    with db.engine.begin() as connection:
        connection.execute(text("UPDATE autores SET tipo='coautor' WHERE tipo IS NULL OR tipo=''"))
        connection.execute(text(
            "UPDATE autores SET tipo='principal' WHERE id IN ("
            "SELECT MIN(a.id) FROM autores a JOIN projetos p ON p.id=a.projeto_id "
            "WHERE a.usuario_id=p.usuario_id GROUP BY a.projeto_id)"
        ))
        connection.execute(text(
            "INSERT INTO autores (tipo, usuario_id, projeto_id) "
            "SELECT 'principal', p.usuario_id, p.id FROM projetos p "
            "WHERE NOT EXISTS (SELECT 1 FROM autores a WHERE a.projeto_id=p.id AND a.usuario_id=p.usuario_id)"
        ))


def _migrate_legacy_uploads():
    """Move referências antigas para as tabelas normalizadas sem apagar legado."""
    tables = set(inspect(db.engine).get_table_names())
    if not {'projetos', 'projeto_imagens', 'projeto_arquivos'}.issubset(tables):
        return

    with db.engine.begin() as connection:
        projetos = connection.execute(
            text('SELECT id, estrutura, arquivo FROM projetos')
        ).mappings()
        for projeto in projetos:
            caminhos = [item.strip() for item in (projeto['estrutura'] or '').split(',') if item.strip()]
            for ordem, caminho in enumerate(caminhos):
                exists = connection.execute(
                    text('SELECT 1 FROM projeto_imagens WHERE projeto_id=:pid AND caminho=:caminho'),
                    {'pid': projeto['id'], 'caminho': caminho},
                ).first()
                if not exists:
                    connection.execute(text(
                        'INSERT INTO projeto_imagens '
                        '(caminho, nome_original, is_capa, ordem, projeto_id) '
                        'VALUES (:caminho, :nome, :capa, :ordem, :pid)'
                    ), {
                        'caminho': caminho,
                        'nome': caminho.rsplit('/', 1)[-1],
                        'capa': ordem == 0,
                        'ordem': ordem,
                        'pid': projeto['id'],
                    })

            caminho_arquivo = projeto['arquivo']
            if caminho_arquivo:
                exists = connection.execute(
                    text('SELECT 1 FROM projeto_arquivos WHERE projeto_id=:pid AND caminho=:caminho'),
                    {'pid': projeto['id'], 'caminho': caminho_arquivo},
                ).first()
                if not exists:
                    nome = caminho_arquivo.rsplit('/', 1)[-1]
                    extensao = nome.rsplit('.', 1)[-1].lower() if '.' in nome else ''
                    connection.execute(text(
                        'INSERT INTO projeto_arquivos '
                        '(caminho, nome_original, extensao, tamanho, ordem, projeto_id) '
                        'VALUES (:caminho, :nome, :extensao, 0, 0, :pid)'
                    ), {
                        'caminho': caminho_arquivo,
                        'nome': nome,
                        'extensao': extensao,
                        'pid': projeto['id'],
                    })
