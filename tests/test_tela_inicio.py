"""A tela de início é servida e não referencia nada que não exista."""
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]


def test_pagina_tem_as_regioes_que_o_js_preenche(cliente):
    corpo = cliente.get("/").get_data(as_text=True)
    for regiao in ["home-hero", "home-updates", "home-trending",
                   "home-favorites", "home-alert-msg"]:
        assert f'id="{regiao}"' in corpo


def test_js_linka_por_slug_e_nao_por_nome():
    """`jogo` é o nome de exibição; linkar por ele gera
    /jogo/Grand Theft Auto V Legacy."""
    texto = (RAIZ / "view/estatico/js/inicio.js").read_text(encoding="utf-8")
    assert "jogo_slug" in texto


def test_js_so_chama_o_endpoint_da_tela():
    texto = (RAIZ / "view/estatico/js/inicio.js").read_text(encoding="utf-8")
    assert "/api/v1/telas/inicio" in texto
