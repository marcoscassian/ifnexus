from functools import wraps
from flask import flash, redirect, url_for
from flask_login import current_user, login_required

def suap_required(f):
    #Decorator que garante que o usuário esteja logado e seja aluno ou docente (SUAP).
    @wraps(f)
    @login_required  # garante que o usuário esteja logado
    def decorated_function(*args, **kwargs):
        if current_user.tipo_usuario not in ['Aluno', 'Docente']:
            flash("Autentique sua conta com o SUAP por favor", "error")
            return redirect(url_for('meu_perfil'))
        return f(*args, **kwargs)
    return decorated_function

