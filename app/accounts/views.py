"""Rotas de autenticação, nas mesmas URLs que o allauth servia."""

from urllib.parse import urlsplit

from flask import Blueprint, flash, redirect, render_template, request, session, url_for
from flask_login import login_required, login_user, logout_user
from sqlalchemy import or_
from werkzeug.security import check_password_hash, generate_password_hash

from app.accounts.forms import LoginForm, SignupForm
from app.accounts.models import User
from app.extensions import db

bp = Blueprint("accounts", __name__, url_prefix="/accounts")

# Hash descartável, comparado quando a conta não existe, para que "conta
# inexistente", "conta inativa" e "senha errada" custem o mesmo tempo. O
# `ModelBackend` do Django faz o mesmo (ticket #20760): sem isto o tempo de
# resposta revela o que a mensagem de erro se recusa a dizer.
_HASH_EQUALIZADOR = generate_password_hash("laaclab-timing-equalizer")


@bp.route("/login/", methods=["GET", "POST"])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        identificador = form.username.data.strip()
        usuario = (
            db.session.query(User)
            .filter(
                or_(
                    User.username == identificador,
                    User.email == identificador.lower(),
                )
            )
            .first()
        )
        if usuario is not None:
            senha_confere = usuario.check_password(form.password.data)
        else:
            senha_confere = check_password_hash(_HASH_EQUALIZADOR, form.password.data)
        if usuario is not None and usuario.is_active and senha_confere:
            # Cycla a sessão antes de autenticar: o Django faz o mesmo com
            # `cycle_key()`. Com sessão assinada em cookie o fixation
            # clássico não se aplica, mas sem isto o token de CSRF emitido
            # antes do login continua válido depois — e a partir da fatia 1b
            # a sessão passa a carregar estado de verdade.
            session.clear()
            login_user(usuario)
            return redirect(_destino_seguro() or url_for("core.home"))
        # Mensagem única para credencial errada e usuário inativo: dizer qual
        # dos dois falhou entrega ao atacante se a conta existe.
        flash("Usuário ou senha inválidos.", "danger")
    return render_template("account/login.html", form=form)


@bp.route("/signup/", methods=["GET", "POST"])
def signup():
    form = SignupForm()
    if form.validate_on_submit():
        username = form.username.data.strip()
        email = form.email.data.strip().lower()
        if db.session.query(User).filter_by(username=username).first():
            flash("Esse usuário já existe.", "danger")
        elif db.session.query(User).filter_by(email=email).first():
            flash("Esse e-mail já está em uso.", "danger")
        else:
            usuario = User(username=username, email=email)
            usuario.set_password(form.password1.data)
            db.session.add(usuario)
            db.session.commit()
            session.clear()  # mesma rotação de sessão do login, ver acima
            login_user(usuario)  # ACCOUNT_LOGIN_ON_SIGNUP do allauth
            return redirect(url_for("core.home"))
    return render_template("account/signup.html", form=form)


@bp.route("/logout/", methods=["GET", "POST"])
@login_required
def logout():
    if request.method == "POST":
        logout_user()
        session.clear()  # equivalente ao flush() do Django
        return redirect(url_for("accounts.login"))
    return render_template("account/logout.html")


def _destino_seguro() -> str | None:
    """O `?next=` só é honrado se for um caminho relativo desta aplicação.

    Aceitar um destino absoluto aqui seria um open redirect: o atacante manda
    `/accounts/login/?next=https://phishing.example` e a vítima é levada para
    lá já tendo digitado a senha no domínio real.

    Checar por prefixo não basta. No padrão WHATWG a barra invertida é
    separador de caminho para http/https, então `/\\evil.example` chega aqui
    parecendo relativo e o browser resolve como `https://evil.example`. Por
    isso normalizamos as barras antes de decidir, e devolvemos o valor
    normalizado — nunca o original.

    Lê de `request.values` (query string **e** corpo do form), não só de
    `request.args`: o template posta para `url_for('accounts.login')`, sem
    query string, e carrega o `next` num campo oculto do form — é assim que
    o navegador de fato manda o valor de volta.
    """
    destino = request.values.get("next", "")
    if not destino:
        return None
    normalizado = destino.replace("\\", "/")
    partes = urlsplit(normalizado)
    if partes.scheme or partes.netloc:
        return None
    if not normalizado.startswith("/") or normalizado.startswith("//"):
        return None
    return normalizado
