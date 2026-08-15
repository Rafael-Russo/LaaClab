import pytest

from app.accounts.models import User
from app.core.query import paginar
from app.extensions import db


@pytest.fixture
def usuarios(app):
    for i in range(25):
        usuario = User(username=f"user{i:02d}", email=f"user{i:02d}@example.com")
        usuario.set_password("segredo123")
        db.session.add(usuario)
    db.session.commit()


def envelope(app, url, **kwargs):
    with app.test_request_context(url):
        return paginar(db.session.query(User), **kwargs)


def test_envelope_tem_as_quatro_chaves_do_drf(app, usuarios):
    resultado = envelope(app, "/x")
    assert set(resultado) == {"count", "next", "previous", "results"}


def test_count_e_o_total_e_nao_o_da_pagina(app, usuarios):
    resultado = envelope(app, "/x")
    assert resultado["count"] == 25
    assert len(resultado["results"]) == 20


def test_primeira_pagina_nao_tem_previous(app, usuarios):
    resultado = envelope(app, "/x")
    assert resultado["previous"] is None
    assert resultado["next"] is not None
    assert "page=2" in resultado["next"]


def test_ultima_pagina_nao_tem_next(app, usuarios):
    resultado = envelope(app, "/x?page=2")
    assert resultado["next"] is None
    assert resultado["previous"] is not None
    assert len(resultado["results"]) == 5


def test_page_invalida_cai_para_a_primeira(app, usuarios):
    assert envelope(app, "/x?page=nao-numero")["previous"] is None
    assert envelope(app, "/x?page=0")["previous"] is None
    assert envelope(app, "/x?page=999")["results"] == []


def test_search_filtra_pelos_campos_declarados(app, usuarios):
    resultado = envelope(app, "/x?search=user01", search_fields=["username"])
    assert resultado["count"] == 1
    assert resultado["results"][0].username == "user01"


def test_search_e_case_insensitive_e_parcial(app, usuarios):
    resultado = envelope(app, "/x?search=USER1", search_fields=["username"])
    assert resultado["count"] == 10  # user10..user19


def test_search_e_ignorado_sem_campos_declarados(app, usuarios):
    assert envelope(app, "/x?search=user01")["count"] == 25


def test_ordering_ascendente(app, usuarios):
    resultado = envelope(app, "/x?ordering=username", ordering_fields=["username"])
    assert resultado["results"][0].username == "user00"


def test_ordering_descendente_com_menos(app, usuarios):
    resultado = envelope(app, "/x?ordering=-username", ordering_fields=["username"])
    assert resultado["results"][0].username == "user24"


def test_ordering_fora_da_allowlist_e_ignorado(app, usuarios):
    """Campo não declarado não pode virar `order_by` — é superfície de ataque
    e fonte de 500 por coluna inexistente."""
    resultado = envelope(
        app, "/x?ordering=password_hash", ordering_fields=["username"],
        default_ordering="username",
    )
    assert resultado["results"][0].username == "user00"


def test_default_ordering_quando_nada_e_pedido(app, usuarios):
    resultado = envelope(app, "/x", default_ordering="-username")
    assert resultado["results"][0].username == "user24"
