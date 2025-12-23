from flask import Blueprint

projetos_bp = Blueprint(
    "projetos",
    __name__
)

from . import crud, exibicao, helpers, interacoes
