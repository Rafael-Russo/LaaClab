from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]


def _codigo():
    import sys
    sys.path.insert(0, str(RAIZ / "tests"))
    from test_frontend import _sem_comentarios

    return _sem_comentarios(
        (RAIZ / "view/estatico/js/configuracao.js").read_text(encoding="utf-8")
    )


def test_pagina_tem_os_campos(cliente):
    corpo = cliente.get("/configuracao").get_data(as_text=True)
    for campo in ["senha_atual", "senha_nova", "apelido", "bio"]:
        assert f'name="{campo}"' in corpo


def test_guarda_os_tokens_novos_depois_de_trocar_a_senha():
    """A troca revoga a sessão antiga de propósito. Sem guardar os
    tokens que ela devolve, a pessoa é expulsa no exato momento em que
    se protegeu."""
    texto = _codigo()
    assert "/api/auth/senha" in texto
    assert "guardarSessao" in texto


def test_erro_de_senha_atual_aparece_no_campo():
    assert ".erros" in _codigo()
