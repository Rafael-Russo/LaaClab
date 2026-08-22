from pathlib import Path

from test_frontend import _sem_comentarios

RAIZ = Path(__file__).resolve().parents[1]


def test_pagina_tem_as_regioes(cliente):
    corpo = cliente.get("/alertas").get_data(as_text=True)
    for regiao in ["al-list", "al-summary", "al-favorites"]:
        assert f'id="{regiao}"' in corpo


def test_usa_o_rotulo_pronto_da_api():
    """`severidade_rotulo` já vem em português; montar outro no cliente
    cria uma segunda tabela de vocabulário que diverge da primeira."""
    texto = _sem_comentarios((RAIZ / "view/estatico/js/alertas.js").read_text(encoding="utf-8"))
    assert "severidade_rotulo" in texto
    assert "/api/v1/telas/alertas" in texto
