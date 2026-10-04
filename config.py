import os


database_url = os.environ.get('DATABASE_URL')
if database_url and database_url.startswith('postgres://'):
    database_url = database_url.replace('postgres://', 'postgresql://', 1)

class Config:
    """Configurações padrão da aplicação"""
    
    # Banco de dados
    SQLALCHEMY_DATABASE_URI = database_url or 'sqlite:///ifnexus.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Chave secreta para sessões
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-production'

    # OAuth do SUAP. Na Vercel, SUAP_REDIRECT_URI deve ser a URL pública
    # cadastrada no cliente OAuth (ex.: https://dominio.com/auth/login).
    SUAP_BASE_URL = os.environ.get('SUAP_BASE_URL', 'https://suap.ifrn.edu.br').rstrip('/')
    SUAP_CLIENT_ID = os.environ.get('SUAP_CLIENT_ID', 'G4IXTGHpxPafBmBGszCAuvxe6iBZgoK3W83HIUSE')
    SUAP_REDIRECT_URI = os.environ.get('SUAP_REDIRECT_URI')
    SUAP_SCOPE = os.environ.get('SUAP_SCOPE', 'identificacao email documentos_pessoais')
    
    # Flask-Login
    REMEMBER_COOKIE_DURATION = 7 * 24 * 60 * 60  # 7 dias
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    SESSION_COOKIE_SECURE = bool(os.environ.get('VERCEL'))
    
    # Upload de arquivos
    UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), 'static', 'uploads')
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max file size
