import pytest


def _cabecalho(cliente, nome="gamer"):
    corpo = cliente.post(
        "/api/auth/registro",
        json={"nome_usuario": nome, "email": f"{nome}@l.dev", "senha": "senha123"},
    ).get_json()
    return {"Authorization": f"Bearer {corpo['token_acesso']}"}


@pytest.fixture
def mundo(cliente, app):
    """Um usuário comum e dois jogos no catálogo — o bastante para a
    paginação (por_pagina=1) ter uma segunda página."""
    from app.composicao import montar_servicos
    from app.extensions import db
    from app.models import Usuario

    cabecalho = _cabecalho(cliente)

    chefe = Usuario(nome_usuario="chefe", email="chefe@l.dev", is_admin=True)
    chefe.definir_senha("senha123")
    db.session.add(chefe)
    db.session.commit()

    servicos = montar_servicos()
    instavel = servicos.jogos.criar({"nome": "Cyberpunk 2077"}, usuario=chefe)
    calmo = servicos.jogos.criar({"nome": "Hollow Knight"}, usuario=chefe)

    return {"cabecalho": cabecalho, "instavel": instavel, "calmo": calmo}


def test_explorar_devolve_envelope_de_paginacao(cliente, mundo):
    corpo = cliente.get(
        "/api/v1/telas/explorar", headers=mundo["cabecalho"]
    ).get_json()
    assert set(corpo) >= {
        "itens", "pagina", "por_pagina", "total", "paginas",
        "proxima", "anterior", "generos",
    }


def test_cartao_traz_o_estado_da_biblioteca_do_usuario(cliente, mundo, app):
    """O botão "Adicionar" precisa saber o que já está na biblioteca.
    Consumir o CRUD de jogos não daria isso — foi o bloqueador da
    revisão final da fase 1."""
    from app.extensions import db
    from app.models import BibliotecaUsuario, Jogo, Usuario

    comum = db.session.execute(
        db.select(Usuario).where(Usuario.nome_usuario == "gamer")
    ).scalars().first()
    jogo = db.session.execute(db.select(Jogo)).scalars().first()
    db.session.add(BibliotecaUsuario(usuario_id=comum.id, jogo_id=jogo.id,
                                     favorito=True))
    db.session.commit()

    corpo = cliente.get(
        "/api/v1/telas/explorar", headers=mundo["cabecalho"]
    ).get_json()
    por_slug = {c["slug"]: c for c in corpo["itens"]}
    assert por_slug[jogo.slug]["na_biblioteca"] is True
    assert por_slug[jogo.slug]["favorito"] is True


def test_proxima_preserva_os_parametros(cliente, mundo):
    """Seguir `proxima` sem os parâmetros faria a página 2 voltar à ordem
    padrão, misturando resultados fora de ordem no "Carregar mais"."""
    corpo = cliente.get(
        "/api/v1/telas/explorar?por_pagina=1&ordenar_por=-pontuacao",
        headers=mundo["cabecalho"],
    ).get_json()
    assert corpo["proxima"] is not None
    assert "ordenar_por=-pontuacao" in corpo["proxima"]
    assert "pagina=2" in corpo["proxima"]


def test_sem_token_responde_401(cliente):
    assert cliente.get("/api/v1/telas/explorar").status_code == 401


def test_jogo_na_biblioteca_sem_ser_favorito(cliente, mundo, app):
    """O par que ninguém testava. `na_biblioteca` e `favorito` são
    estados diferentes, e confundi-los foi o bloqueador da fase 1:
    a tela mostrava coração cheio em jogo que só estava na lista."""
    from app.extensions import db
    from app.models import BibliotecaUsuario, Jogo, Usuario

    comum = db.session.execute(
        db.select(Usuario).where(Usuario.nome_usuario == "gamer")
    ).scalars().first()
    jogos = db.session.execute(db.select(Jogo)).scalars().all()
    assert len(jogos) >= 2, "o cenário precisa de dois jogos"

    db.session.add(
        BibliotecaUsuario(usuario_id=comum.id, jogo_id=jogos[0].id, favorito=False)
    )
    db.session.commit()

    corpo = cliente.get(
        "/api/v1/telas/explorar", headers=mundo["cabecalho"]
    ).get_json()
    por_slug = {c["slug"]: c for c in corpo["itens"]}

    dentro = por_slug[jogos[0].slug]
    assert dentro["na_biblioteca"] is True
    assert dentro["favorito"] is False

    fora = por_slug[jogos[1].slug]
    assert fora["na_biblioteca"] is False
    assert fora["favorito"] is False


def test_bordas_da_paginacao(cliente, mundo):
    """Primeira página não tem anterior; última não tem próxima."""
    primeira = cliente.get(
        "/api/v1/telas/explorar?por_pagina=1", headers=mundo["cabecalho"]
    ).get_json()
    assert primeira["anterior"] is None
    assert primeira["proxima"] is not None

    ultima = cliente.get(
        f"/api/v1/telas/explorar?por_pagina=1&pagina={primeira['paginas']}",
        headers=mundo["cabecalho"],
    ).get_json()
    assert ultima["proxima"] is None
    assert ultima["anterior"] is not None


def test_ordenacao_invalida_e_422_nesta_rota(cliente, mundo):
    """Falhar fechada vale em toda porta de entrada, não só no Service."""
    resposta = cliente.get(
        "/api/v1/telas/explorar?ordenar_por=senha_hash", headers=mundo["cabecalho"]
    )
    assert resposta.status_code == 422


def test_teto_de_paginacao_vale_nesta_rota(cliente, mundo):
    resposta = cliente.get(
        "/api/v1/telas/explorar?por_pagina=500", headers=mundo["cabecalho"]
    ).get_json()
    assert resposta["por_pagina"] <= 100
