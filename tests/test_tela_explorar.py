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
