from pathlib import Path

from test_frontend import _sem_comentarios

RAIZ = Path(__file__).resolve().parents[1]


def test_pagina_tem_a_grade(cliente):
    corpo = cliente.get("/biblioteca").get_data(as_text=True)
    assert 'id="lib-grid"' in corpo


def test_favoritar_usa_entrada_id_e_nao_id_do_jogo():
    """`id` é do jogo, `entrada_id` é da entrada da biblioteca. Trocar
    um pelo outro edita a entrada de outra pessoa ou dá 404."""
    texto = _sem_comentarios((RAIZ / "view/estatico/js/biblioteca.js").read_text(encoding="utf-8"))
    assert "entrada_id" in texto
    assert "/api/v1/biblioteca/" in texto
    assert "PATCH" in texto
