from flask import render_template

from app.telas import bp


@bp.route("/")
def inicio():
    return render_template("telas/inicio.html")


@bp.route("/biblioteca")
def biblioteca():
    return render_template("telas/biblioteca.html")


@bp.route("/bugometro")
def bugometro():
    return render_template("telas/bugometro.html")


@bp.route("/historicos")
def historicos():
    return render_template("telas/historicos.html")


@bp.route("/alertas")
def alertas():
    return render_template("telas/alertas.html")


@bp.route("/comunidade")
def comunidade():
    return render_template("telas/comunidade.html")


@bp.route("/comunidade/topico/<int:topico_id>")
def topico(topico_id: int):
    return render_template("telas/topico.html", topico_id=topico_id)


@bp.route("/jogo/<int:jogo_id>")
def jogo(jogo_id: int):
    return render_template("telas/jogo.html", jogo_id=jogo_id)


@bp.route("/perfil")
def perfil():
    return render_template("telas/perfil.html")


@bp.route("/configuracao")
def configuracao():
    return render_template("telas/configuracao.html")
