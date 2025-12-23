import os

BASE_DIR = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))

STATIC_DIR = os.path.join(BASE_DIR, "static")
UPLOADS_DIR = os.path.join(STATIC_DIR, "uploads")

PROJETOS_DIR = os.path.join(UPLOADS_DIR, "projetos")
USERS_DIR = os.path.join(UPLOADS_DIR, "users")
