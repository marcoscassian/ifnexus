#esse arquivo cria usuários de testes no banco de dados
#use "python scripts\criar_usuarios_teste.py" para rodar esse script

import sys
import os

# adiciona a raiz do projeto ao sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app
from extensions import db, bcrypt
from models import Usuario

with app.app_context():
    usuarios = [
        Usuario(
            nome="Admin IF",
            email="admin@if.edu.br",
            senha=bcrypt.generate_password_hash("123").decode("utf-8"),
            tipo_usuario="Aluno",
            campus="IF Central"
        ),
        Usuario(
            nome="João da Silva",
            email="joao@if.edu.br",
            senha=bcrypt.generate_password_hash("123").decode("utf-8"),
            tipo_usuario="Aluno",
            matricula="202312345",
            campus="IF Central"
        ),
        Usuario(
            nome="Maria Souza",
            email="maria@if.edu.br",
            senha=bcrypt.generate_password_hash("123").decode("utf-8"),
            tipo_usuario="Aluno",
            campus="IF Central"
        )
    ]

    for usuario in usuarios:
        # evita duplicação
        existe = Usuario.query.filter_by(email=usuario.email).first()
        if not existe:
            db.session.add(usuario)

    db.session.commit()
    print("✅ Usuários de teste criados com sucesso!")
