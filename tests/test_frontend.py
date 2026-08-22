"""Testes estruturais do frontend.

Não abrem navegador: verificam que as páginas são servidas, que o que
elas referenciam existe, e que o JS fala com rotas que a API realmente
tem — a classe de erro que mais custou na construção da API, duas
metades corretas isoladamente que não se encontram.

As rotas de página (`ROTAS_DE_PAGINA`) entram na Task 4, quando
`view/paginas/` passa a ter conteúdo. Até lá, testá-las aqui deixaria
o commit vermelho de propósito.
"""

import pytest


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
