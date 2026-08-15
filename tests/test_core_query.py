from urllib.parse import parse_qs, urlsplit

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


def test_paginacao_sem_ordenacao_alguma_e_estavel_entre_paginas(app, usuarios):
    """Sem `?ordering=` e sem `default_ordering`, a query batia direto em
    `LIMIT`/`OFFSET` sem `ORDER BY` nenhum — a ordem entre as duas consultas
    (página 1, página 2) não é garantida pelo banco, então linhas podiam se
    repetir numa página e nunca aparecer na outra. A PK como desempate
    implícito resolve isso mesmo quando nada foi pedido."""
    pagina1 = envelope(app, "/x?page=1")
    pagina2 = envelope(app, "/x?page=2")
    ids = {u.id for u in pagina1["results"]} | {u.id for u in pagina2["results"]}
    assert len(ids) == 25


def test_search_escapa_underscore(app, usuarios):
    """`_` é coringa de um caractere no LIKE — sem escapar, `a_b` bateria em
    qualquer `axb`. Usa nomes fabricados para não depender do padrão
    `userNN` da fixture."""
    extra1 = User(username="a_b", email="a_b@example.com")
    extra1.set_password("segredo123")
    extra2 = User(username="axb", email="axb@example.com")
    extra2.set_password("segredo123")
    db.session.add_all([extra1, extra2])
    db.session.commit()

    resultado = envelope(app, "/x?search=a_b", search_fields=["username"])
    assert resultado["count"] == 1
    assert resultado["results"][0].username == "a_b"


def test_search_escapa_porcentagem(app, usuarios):
    """`%` é coringa de qualquer sequência — sem escapar, `?search=%`
    devolveria a tabela inteira em vez de zero resultados."""
    resultado = envelope(app, "/x?search=%25", search_fields=["username"])
    assert resultado["count"] == 0


def test_search_com_e_comercial_sobrevive_ao_round_trip(app, usuarios):
    """`&` numa busca não pode virar separador de parâmetro na URL devolvida.

    Página 2 sempre tem `previous`, mesmo sem resultado nenhum — é o jeito
    mais direto de forçar `_url_da_pagina` a rodar e inspecionar o que ela
    devolveu.
    """
    resultado = envelope(app, "/x?page=2&search=A%26B", search_fields=["username"])
    query = parse_qs(urlsplit(resultado["previous"]).query)
    assert query["search"] == ["A&B"]


def test_search_com_espaco_sobrevive_ao_round_trip(app, usuarios):
    resultado = envelope(app, "/x?page=2&search=hello%20world", search_fields=["username"])
    query = parse_qs(urlsplit(resultado["previous"]).query)
    assert query["search"] == ["hello world"]


def test_parametro_repetido_e_preservado_no_next(app, usuarios):
    resultado = envelope(app, "/x?page=2&foo=1&foo=2")
    query = parse_qs(urlsplit(resultado["previous"]).query)
    assert query["foo"] == ["1", "2"]
