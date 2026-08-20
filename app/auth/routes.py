from flask import flash, redirect, render_template, request, session, url_for
from flask_login import login_required, login_user, logout_user

from app.auth import bp
from app.auth.forms import CadastrarForm, EntrarForm
from app.auth.service import (
    ApiIndisponivel,
    CredenciaisInvalidas,
    DadosInvalidos,
    autenticar,
    registrar,
)
from app.auth.usuario import Usuario

RECADO_API_FORA = "Não foi possível falar com o servidor. Tente de novo em instantes."


def _destino_seguro(destino: str | None) -> str:
    """Impede que `?next=` mande o usuário para fora do app (open redirect)."""
    if destino and destino.startswith("/") and not destino.startswith("//"):
        return destino
    return url_for("telas.inicio")


@bp.route("/entrar", methods=["GET", "POST"])
def entrar():
    form = EntrarForm()
    if form.validate_on_submit():
        try:
            login_user(Usuario.da_api(autenticar(form.email.data, form.senha.data)))
        except CredenciaisInvalidas:
            flash("E-mail ou senha incorretos.", "erro")
        except ApiIndisponivel:
            flash(RECADO_API_FORA, "erro")
        else:
            return redirect(_destino_seguro(request.args.get("next")))
    return render_template("auth/entrar.html", form=form)


@bp.route("/cadastrar", methods=["GET", "POST"])
def cadastrar():
    form = CadastrarForm()
    if form.validate_on_submit():
        try:
            criado = registrar(form.nome_usuario.data, form.email.data, form.senha.data)
        except DadosInvalidos as erro:
            for campo, mensagens in erro.erros.items():
                for mensagem in mensagens:
                    flash(f"{campo}: {mensagem}", "erro")
        except ApiIndisponivel:
            flash(RECADO_API_FORA, "erro")
        else:
            login_user(Usuario.da_api(criado))
            return redirect(url_for("telas.inicio"))
    return render_template("auth/cadastrar.html", form=form)


@bp.route("/sair", methods=["POST"])
@login_required
def sair():
    logout_user()
    session.clear()
    return redirect(url_for("auth.entrar"))
