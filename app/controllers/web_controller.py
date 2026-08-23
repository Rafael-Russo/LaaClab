"""Serve o frontend estático.

Só devolve arquivo: não chama Service e não toca o banco, então é a
"Tela" da cadeia, não um Controller de domínio. Mesma origem que a API,
o que dispensa CORS e deixa o token viajar num header comum.
"""
from pathlib import Path

from flask import Blueprint, send_from_directory

RAIZ = Path(__file__).resolve().parents[2] / "view"
PAGINAS = RAIZ / "paginas"
ESTATICO = RAIZ / "estatico"

#: rota -> arquivo em `view/paginas/`
PAGINAS_POR_ROTA = {
    "/": "inicio.html",
    "/biblioteca": "biblioteca.html",
    "/bugometro": "bugometro.html",
    "/alertas": "alertas.html",
    "/comunidade": "comunidade.html",
    "/perfil": "perfil.html",
    "/login": "login.html",
    "/registro": "registro.html",
    "/explorar": "explorar.html",
    "/configuracao": "configuracao.html",
}


def criar_blueprint_web() -> Blueprint:
    bp = Blueprint("web", __name__)

    def _servir(arquivo):
        return send_from_directory(PAGINAS, arquivo)

    for rota, arquivo in PAGINAS_POR_ROTA.items():
        bp.add_url_rule(
            rota,
            endpoint=f"pagina_{arquivo.removesuffix('.html')}",
            view_func=(lambda a=arquivo: _servir(a)),
        )

    @bp.get("/jogo/<slug>")
    def pagina_jogo(slug):
        """O mesmo HTML para qualquer slug: o JS lê o último segmento de
        `location.pathname`. É o que substitui o `data-slug` que o
        template Django injetava."""
        return _servir("jogo.html")

    @bp.get("/estatico/<path:caminho>")
    def estatico(caminho):
        return send_from_directory(ESTATICO, caminho)

    return bp
