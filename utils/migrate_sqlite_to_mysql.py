import os
import sqlite3
from pathlib import Path
import sys

from dotenv import load_dotenv
from sqlalchemy import MetaData, create_engine, inspect, text


load_dotenv()


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))
SQLITE_URL = f"sqlite:///{(PROJECT_ROOT / 'instance' / 'ifnexus.db').as_posix()}"
MYSQL_URL = os.environ.get("DATABASE_URL")


def copy_database() -> None:
    if not MYSQL_URL:
        raise RuntimeError("DATABASE_URL nao esta configurada.")
    if not MYSQL_URL.startswith(("mysql://", "mysql+pymysql://")):
        raise RuntimeError("DATABASE_URL deve apontar para um banco MySQL.")

    source = create_engine(SQLITE_URL)
    target = create_engine(MYSQL_URL)

    source_metadata = MetaData()
    source_metadata.reflect(bind=source)
    source_names = set(source_metadata.tables)

    target_metadata = MetaData()
    target_metadata.reflect(bind=target)
    target_names = set(target_metadata.tables)

    if target_names:
        raise RuntimeError(
            "O banco MySQL ja possui tabelas. Interrompendo para evitar sobrescrita."
        )

    os.environ["DATABASE_URL"] = MYSQL_URL
    from app import app, db

    with app.app_context():
        db.create_all()

    with source.begin() as source_connection:
        with target.begin() as target_connection:
            for table in db.metadata.sorted_tables:
                if table.name not in source_names:
                    continue

                source_table = source_metadata.tables[table.name]
                rows = source_connection.execute(source_table.select()).mappings().all()
                if rows:
                    target_connection.execute(table.insert(), [dict(row) for row in rows])

    verify = inspect(target)
    with target.connect() as connection:
        for table_name in verify.get_table_names():
            source_count = (
                source.connect()
                .execute(text(f'SELECT COUNT(*) FROM "{table_name}"'))
                .scalar()
                if table_name in source_names
                else None
            )
            target_count = connection.execute(
                text(f"SELECT COUNT(*) FROM `{table_name}`")
            ).scalar()
            if source_count != target_count:
                raise RuntimeError(
                    f"A verificacao falhou em {table_name}: "
                    f"{source_count} origem, {target_count} destino"
                )


if __name__ == "__main__":
    copy_database()
    print("Migracao concluida e validada.")
