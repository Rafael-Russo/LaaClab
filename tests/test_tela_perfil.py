from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]


def test_pagina_tem_as_regioes(cliente):
    corpo = cliente.get("/perfil").get_data(as_text=True)
    for regiao in ["pf-usuario", "pf-recentes"]:
        assert f'id="{regiao}"' in corpo


def test_js_le_o_endpoint_do_perfil():
    texto = (RAIZ / "view/estatico/js/perfil.js").read_text(encoding="utf-8")
    assert "/api/v1/telas/perfil" in texto
    assert "jogo_slug" in texto
