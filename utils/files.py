import os
from werkzeug.utils import secure_filename
from utils.paths import PROJETOS_DIR

def criar_pastas_projeto(titulo):
    nome_pasta = secure_filename(titulo.lower().replace(" ", "-"))

    base = os.path.join(PROJETOS_DIR, nome_pasta)
    pasta_imagens = os.path.join(base, "imagens")
    pasta_pdfs = os.path.join(base, "pdfs")

    os.makedirs(pasta_imagens, exist_ok=True)
    os.makedirs(pasta_pdfs, exist_ok=True)

    return base, pasta_imagens, pasta_pdfs, nome_pasta
