"""Testes estruturais do frontend.

Não abrem navegador: verificam que as páginas são servidas, que o que
elas referenciam existe, e que o JS fala com rotas que a API realmente
tem — a classe de erro que mais custou na construção da API, duas
metades corretas isoladamente que não se encontram.

As rotas de página (`ROTAS_DE_PAGINA`) entram na Task 4, quando
`view/paginas/` passa a ter conteúdo. Até lá, testá-las aqui deixaria
o commit vermelho de propósito.
"""

from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parent.parent


def test_estatico_serve_o_css(cliente):
    resposta = cliente.get("/estatico/css/estilos.css")
    assert resposta.status_code == 200


ROTAS_DE_PAGINA = [
    "/",
    "/biblioteca",
    "/bugometro",
    "/jogo/cyberpunk-2077",
    "/alertas",
    "/comunidade",
    "/perfil",
    "/login",
    "/registro",
]


@pytest.mark.parametrize("rota", ROTAS_DE_PAGINA)
def test_pagina_responde_html(cliente, rota):
    resposta = cliente.get(rota)
    assert resposta.status_code == 200
    assert resposta.mimetype == "text/html"


def test_guarda_de_casca_acusa_pagina_nao_registrada(tmp_path, monkeypatch):
    """Falhar aberto é pior que não ter guarda: uma página nova que
    ninguém registrou passaria sem verificação e a saída ainda diria
    `Casca OK.`, dando confiança falsa."""
    import importlib.util
    import sys

    caminho = RAIZ / "tools" / "verificar_casca.py"
    spec = importlib.util.spec_from_file_location("verificar_casca", caminho)
    modulo = importlib.util.module_from_spec(spec)
    sys.modules["verificar_casca"] = modulo
    spec.loader.exec_module(modulo)

    for nome in ["inicio.html", "login.html", "orfa.html"]:
        (tmp_path / nome).write_text(
            "<!-- CASCA:INICIO -->x<!-- CASCA:FIM -->", encoding="utf-8"
        )
    monkeypatch.setattr(modulo, "PAGINAS", tmp_path)
    monkeypatch.setattr(
        modulo, "GRUPOS", {"aplicação": ["inicio.html"], "autenticação": ["login.html"]}
    )

    assert modulo.main() == 1
