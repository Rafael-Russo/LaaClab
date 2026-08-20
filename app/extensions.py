from flask import session
from flask_login import LoginManager
from flask_wtf.csrf import CSRFProtect

csrf = CSRFProtect()
login_manager = LoginManager()
login_manager.login_view = "auth.entrar"
login_manager.login_message = "Entre para continuar."
login_manager.login_message_category = "aviso"


@login_manager.user_loader
def carregar_usuario(user_id: str):
    """Reconstrói o usuário a partir da sessão assinada — não há banco.

    O `login_user` do Flask-Login grava o id no cookie; os demais campos
    ficam na chave "usuario" da mesma sessão, gravada em `auth.routes`.
    """
    from app.auth.usuario import Usuario

    dados = session.get("usuario")
    if not dados or str(dados.get("id")) != str(user_id):
        return None
    return Usuario.da_sessao(dados)
