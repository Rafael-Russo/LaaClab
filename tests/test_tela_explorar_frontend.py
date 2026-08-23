"""Testes estruturais da tela Explorar (frontend).

Não confundir com tests/test_tela_explorar.py, que testa a API
(`GET /api/v1/telas/explorar`). Este arquivo testa a página e o JS que a
consomem: as regiões da tela, o envelope de paginação novo (`itens`,
não `.results`/`.next` do DRF herdado) e o POST de adicionar à
biblioteca (`jogo_id`).
"""
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]


def _codigo():
    import sys
    sys.path.insert(0, str(RAIZ / "tests"))
    from test_frontend import _sem_comentarios

    return _sem_comentarios(
        (RAIZ / "view/estatico/js/explorar.js").read_text(encoding="utf-8")
    )


def test_pagina_tem_as_regioes(cliente):
    corpo = cliente.get("/explorar").get_data(as_text=True)
    for regiao in ["ex-busca", "ex-genero", "ex-ordem", "ex-grade", "ex-mais"]:
        assert f'id="{regiao}"' in corpo


def test_usa_o_envelope_novo_e_nao_o_do_drf():
    texto = _codigo()
    assert "/api/v1/telas/explorar" in texto
    assert "itens" in texto
    assert ".results" not in texto
    assert ".next" not in texto


def test_adicionar_a_biblioteca_manda_jogo_id():
    texto = _codigo()
    assert "/api/v1/biblioteca" in texto
    assert "jogo_id" in texto
