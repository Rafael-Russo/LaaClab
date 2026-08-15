"""Rotas de autenticação, nas mesmas URLs que o allauth servia."""

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import login_required, login_user, logout_user
from sqlalchemy import or_

from app.accounts.forms import LoginForm, SignupForm
from app.accounts.models import User
from app.extensions import db

bp = Blueprint("accounts", __name__, url_prefix="/accounts")


@bp.route("/login/", methods=["GET", "POST"])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        identificador = form.username.data.strip()
        usuario = (
            db.session.query(User)
            .filter(or_(User.username == identificador, User.email == identificador))
            .first()
        )
        if usuario and usuario.is_active and usuario.check_password(form.password.data):
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
            login_user(usuario)  # ACCOUNT_LOGIN_ON_SIGNUP do allauth
            return redirect(url_for("core.home"))
    return render_template("account/signup.html", form=form)


@bp.route("/logout/", methods=["GET", "POST"])
@login_required
def logout():
    if request.method == "POST":
        logout_user()
        return redirect(url_for("accounts.login"))
    return render_template("account/logout.html")


def _destino_seguro() -> str | None:
    """O `?next=` só é honrado se for um caminho relativo desta aplicação.

    Aceitar um destino absoluto aqui seria um open redirect: o atacante manda
    `/accounts/login/?next=https://phishing.example` e a vítima é levada para
    lá já tendo digitado a senha no domínio real.
    """
    destino = request.args.get("next", "")
    if destino.startswith("/") and not destino.startswith("//"):
        return destino
    return None
