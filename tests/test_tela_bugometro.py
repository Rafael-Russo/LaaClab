from pathlib import Path

from test_frontend import _sem_comentarios

RAIZ = Path(__file__).resolve().parents[1]


def test_pagina_tem_as_regioes(cliente):
    corpo = cliente.get("/bugometro").get_data(as_text=True)
    for regiao in ["bm-metrics", "bm-bugs", "bm-chart", "bm-activity", "bm-top"]:
        assert f'id="{regiao}"' in corpo


def test_relatar_bug_manda_jogo_id():
    """`POST /relatos-bug` exige `jogo_id` e `titulo`. A tela só conhece
    o slug, então o id tem que sair do payload."""
    texto = _sem_comentarios((RAIZ / "view/estatico/js/bugometro.js").read_text(encoding="utf-8"))
    assert "/api/v1/relatos-bug" in texto
    assert "jogo_id" in texto
