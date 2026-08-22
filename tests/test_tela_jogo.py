from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]


def test_qualquer_slug_serve_a_mesma_pagina(cliente):
    for slug in ["cyberpunk-2077", "um-slug-qualquer"]:
        assert cliente.get(f"/jogo/{slug}").status_code == 200


def test_js_le_o_slug_da_url():
    """O `data-slug` era injetado pelo template Django e morreu com ele."""
    texto = (RAIZ / "view/estatico/js/jogo.js").read_text(encoding="utf-8")
    assert "location.pathname" in texto
    assert "dataset.slug" not in texto


def test_comentar_e_relatar_mandam_jogo_id():
    texto = (RAIZ / "view/estatico/js/jogo.js").read_text(encoding="utf-8")
    assert "/api/v1/avaliacoes" in texto
    assert "/api/v1/relatos-bug" in texto
    assert "comentario" in texto
    assert "jogo_id" in texto
