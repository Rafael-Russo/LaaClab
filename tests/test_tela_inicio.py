"""A tela de início é servida e não referencia nada que não exista."""
import re
from pathlib import Path

from test_frontend import _sem_comentarios

RAIZ = Path(__file__).resolve().parents[1]


def test_pagina_tem_as_regioes_que_o_js_preenche(cliente):
    corpo = cliente.get("/").get_data(as_text=True)
    for regiao in ["home-hero", "home-updates", "home-trending",
                   "home-favorites", "home-alert-msg"]:
        assert f'id="{regiao}"' in corpo


def test_js_nao_linka_jogo_pelo_nome_de_exibicao():
    """`jogo` é o nome de exibição; linkar por ele gera
    /jogo/Grand Theft Auto V Legacy. Esta tela não constrói link
    nenhum diretamente — banners e atualizações não linkam, e os
    favoritos passam por `Api.cartaoDeJogo`, que já usa `slug`. Então
    nenhuma concatenação `"/jogo/" + algo` pode aparecer aqui a menos
    que `algo` seja um slug."""
    texto = _sem_comentarios((RAIZ / "view/estatico/js/inicio.js").read_text(encoding="utf-8"))
    for casamento in re.finditer(r'"/jogo/"\s*\+\s*([\w.]+)', texto):
        alvo = casamento.group(1)
        assert alvo.endswith("slug"), f"link por nome de exibição: {casamento.group(0)}"


def test_js_so_chama_o_endpoint_da_tela():
    texto = _sem_comentarios((RAIZ / "view/estatico/js/inicio.js").read_text(encoding="utf-8"))
    assert "/api/v1/telas/inicio" in texto
