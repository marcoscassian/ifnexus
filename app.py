from flask import Flask
from werkzeug.middleware.proxy_fix import ProxyFix
from extensions import db, login_manager, bcrypt

from controllers.auth import auth_bp
from controllers.main import main_bp
from controllers.projetos import projetos_bp
from controllers.usuarios import usuarios_bp

from models import Usuario
from utils.db_migrations import ensure_project_schema

app = Flask(__name__)
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)

# configurações
app.config.from_object("config.Config")

# inicializa extensões
db.init_app(app)
login_manager.init_app(app)
bcrypt.init_app(app)

# flask-Login
login_manager.login_view = "auth.login"
login_manager.login_message_category = "error"

# blueprints
app.register_blueprint(auth_bp)
app.register_blueprint(main_bp)
app.register_blueprint(projetos_bp)
app.register_blueprint(usuarios_bp)

with app.app_context():
    db.create_all()
    ensure_project_schema()

@login_manager.user_loader
def load_user(user_id):
    return Usuario.query.get(int(user_id))

if __name__ == '__main__':
    app.run(debug=True)
