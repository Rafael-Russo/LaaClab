import pytest


def _registrar(cliente, nome, admin=False):
    corpo = cliente.post(
        "/api/auth/registro",
        json={
            "nome_usuario": nome,
            "email": f"{nome}@l.dev",
            "senha": "senha123",
        },
    ).get_json()

    if admin:
        from app.extensions import db
        from app.models import Usuario

        usuario = db.session.get(Usuario, corpo["usuario"]["id"])
        usuario.is_admin = True
        db.session.commit()

    return corpo


def _id_do_token(cliente, cabecalho):
    return cliente.get("/api/v1/eu", headers=cabecalho).get_json()["id"]


@pytest.fixture
def cabecalho(cliente, app):
    """Conta ADMINISTRADORA.

    A maioria dos testes deste arquivo exercita o catálogo (jogos,
    gêneros, alertas), e escrever nele exige admin — era operação do
    Django admin antes da migração. Para testar privilégio, use
    `cabecalho_comum`.
    """
    corpo = _registrar(cliente, "gamer", admin=True)
    return {"Authorization": f"Bearer {corpo['token_acesso']}"}


@pytest.fixture
def cabecalho_admin(cabecalho):
    """Apelido explícito, para os testes em que o privilégio é o assunto."""
    return cabecalho


@pytest.fixture
def cabecalho_comum(cliente, app):
    """Conta recém-registrada, sem privilégio nenhum."""
    corpo = _registrar(cliente, "novato")
    return {"Authorization": f"Bearer {corpo['token_acesso']}"}


def test_criar_exige_autenticacao(cliente):
    resposta = cliente.post("/api/v1/jogos", json={"nome": "Hades"})
    assert resposta.status_code == 401
    assert resposta.get_json() == {"erro": "Autenticação necessária."}


def test_criar_devolve_201_com_o_recurso(cliente, cabecalho):
    resposta = cliente.post("/api/v1/jogos", json={"nome": "Hades"}, headers=cabecalho)
    assert resposta.status_code == 201
    assert resposta.get_json()["nome"] == "Hades"


def test_criar_sem_campo_obrigatorio_devolve_422(cliente, cabecalho):
    resposta = cliente.post("/api/v1/jogos", json={}, headers=cabecalho)
    assert resposta.status_code == 422
    assert "nome" in resposta.get_json()["erros"]


def test_criar_com_campo_desconhecido_devolve_422(cliente, cabecalho):
    resposta = cliente.post(
        "/api/v1/jogos", json={"nome": "X", "id": 9}, headers=cabecalho
    )
    assert resposta.status_code == 422


def test_listar_devolve_envelope_em_portugues(cliente, cabecalho):
    for indice in range(3):
        cliente.post(
            "/api/v1/jogos", json={"nome": f"Jogo {indice}"}, headers=cabecalho
        )
    corpo = cliente.get("/api/v1/jogos").get_json()
    assert set(corpo) == {
        "itens", "pagina", "por_pagina", "total", "paginas", "proxima", "anterior",
    }
    assert corpo["total"] == 3
    assert corpo["por_pagina"] == 20
    assert corpo["anterior"] is None
    assert corpo["proxima"] is None


def test_proxima_e_caminho_relativo_que_o_front_pode_seguir(cliente, cabecalho):
    for indice in range(25):
        cliente.post(
            "/api/v1/jogos", json={"nome": f"Jogo {indice:02d}"}, headers=cabecalho
        )
    corpo = cliente.get("/api/v1/jogos?por_pagina=10").get_json()
    assert corpo["proxima"] == "/api/v1/jogos?pagina=2&por_pagina=10"

    segunda = cliente.get(corpo["proxima"]).get_json()
    assert segunda["pagina"] == 2
    assert segunda["anterior"] == "/api/v1/jogos?pagina=1&por_pagina=10"


def test_leitura_e_publica(cliente):
    assert cliente.get("/api/v1/jogos").status_code == 200


def test_detalhe_inexistente_devolve_404_em_json(cliente):
    resposta = cliente.get("/api/v1/jogos/9999")
    assert resposta.status_code == 404
    assert resposta.get_json() == {"erro": "Jogo não encontrado."}


def test_atualizacao_parcial(cliente, cabecalho):
    criado = cliente.post(
        "/api/v1/jogos", json={"nome": "Hades", "metacritic": 93}, headers=cabecalho
    ).get_json()
    resposta = cliente.put(
        f"/api/v1/jogos/{criado['id']}", json={"nome": "Hades II"}, headers=cabecalho
    )
    assert resposta.status_code == 200
    corpo = resposta.get_json()
    assert corpo["nome"] == "Hades II"
    assert corpo["metacritic"] == 93


def test_remover_devolve_204(cliente, cabecalho):
    criado = cliente.post(
        "/api/v1/jogos", json={"nome": "Braid"}, headers=cabecalho
    ).get_json()
    assert cliente.delete(
        f"/api/v1/jogos/{criado['id']}", headers=cabecalho
    ).status_code == 204
    assert cliente.get(f"/api/v1/jogos/{criado['id']}").status_code == 404


def test_ordenacao_fora_da_allowlist_e_recusada(cliente):
    """Interpolar o parâmetro direto no ORDER BY seria injeção."""
    resposta = cliente.get("/api/v1/jogos?ordenar_por=senha_hash")
    assert resposta.status_code == 422
    assert "ordenar_por" in resposta.get_json()["erros"]


def test_conteudo_de_outro_usuario_nao_pode_ser_editado(cliente, cabecalho):
    jogo = cliente.post(
        "/api/v1/jogos", json={"nome": "Tunic"}, headers=cabecalho
    ).get_json()
    topico = cliente.post(
        "/api/v1/topicos",
        json={"titulo": "Meu tópico", "jogo_id": jogo["id"]},
        headers=cabecalho,
    ).get_json()

    outro = cliente.post(
        "/api/auth/registro",
        json={"nome_usuario": "outro", "email": "o@l.dev", "senha": "senha123"},
    ).get_json()
    invasor = {"Authorization": f"Bearer {outro['token_acesso']}"}

    resposta = cliente.put(
        f"/api/v1/topicos/{topico['id']}", json={"titulo": "Invadido"}, headers=invasor
    )
    assert resposta.status_code == 403
    assert resposta.get_json() == {"erro": "Acesso negado."}


def test_autor_e_gravado_automaticamente(cliente, cabecalho_admin, cabecalho_comum):
    jogo = cliente.post(
        "/api/v1/jogos", json={"nome": "Celeste"}, headers=cabecalho_admin
    ).get_json()
    topico = cliente.post(
        "/api/v1/topicos",
        json={"titulo": "Dica de speedrun", "jogo_id": jogo["id"]},
        headers=cabecalho_comum,
    ).get_json()
    # Confere o id exato: gravar o autor errado passaria num `is not None`.
    assert topico["usuario_id"] == _id_do_token(cliente, cabecalho_comum)


# --- Catálogo é backoffice: escrita exige admin -------------------------

def test_conta_comum_nao_cria_jogo(cliente, cabecalho_comum):
    resposta = cliente.post(
        "/api/v1/jogos", json={"nome": "Pirata"}, headers=cabecalho_comum
    )
    assert resposta.status_code == 403
    assert resposta.get_json() == {"erro": "Acesso negado."}


def test_conta_comum_nao_apaga_jogo_do_catalogo(cliente, cabecalho_comum, cabecalho_admin):
    """Sem esta trava, qualquer conta recém-registrada apaga o catálogo."""
    jogo = cliente.post(
        "/api/v1/jogos", json={"nome": "Hades"}, headers=cabecalho_admin
    ).get_json()

    assert cliente.delete(
        f"/api/v1/jogos/{jogo['id']}", headers=cabecalho_comum
    ).status_code == 403
    assert cliente.get(f"/api/v1/jogos/{jogo['id']}").status_code == 200


def test_admin_administra_o_catalogo(cliente, cabecalho_admin):
    jogo = cliente.post(
        "/api/v1/jogos", json={"nome": "Tunic"}, headers=cabecalho_admin
    ).get_json()
    assert cliente.delete(
        f"/api/v1/jogos/{jogo['id']}", headers=cabecalho_admin
    ).status_code == 204


def test_conta_comum_ainda_publica_conteudo_proprio(cliente, cabecalho_comum, cabecalho_admin):
    """A trava do catálogo não pode ter fechado o conteúdo do usuário."""
    jogo = cliente.post(
        "/api/v1/jogos", json={"nome": "Celeste"}, headers=cabecalho_admin
    ).get_json()
    resposta = cliente.post(
        "/api/v1/topicos",
        json={"titulo": "Meu tópico", "jogo_id": jogo["id"]},
        headers=cabecalho_comum,
    )
    assert resposta.status_code == 201


# --- Paginação preserva os filtros --------------------------------------

def test_proxima_preserva_ordenar_por(cliente, cabecalho_admin):
    """Seguir `proxima` sem o `ordenar_por` faria a página 2 voltar à
    ordem padrão, misturando resultados fora de ordem."""
    for indice in range(25):
        cliente.post(
            "/api/v1/jogos",
            json={"nome": f"Jogo {indice:02d}", "metacritic": indice},
            headers=cabecalho_admin,
        )

    corpo = cliente.get(
        "/api/v1/jogos?por_pagina=10&ordenar_por=-metacritic"
    ).get_json()
    assert "ordenar_por=-metacritic" in corpo["proxima"]

    segunda = cliente.get(corpo["proxima"]).get_json()
    assert segunda["pagina"] == 2
    notas = [j["metacritic"] for j in segunda["itens"]]
    assert notas == sorted(notas, reverse=True)


# --- Usuário só administra a si mesmo -----------------------------------

def test_usuario_nao_edita_outro_usuario(cliente, cabecalho_comum):
    outro = cliente.post(
        "/api/auth/registro",
        json={"nome_usuario": "alheio", "email": "a@l.dev", "senha": "senha123"},
    ).get_json()

    resposta = cliente.put(
        f"/api/v1/usuarios/{outro['usuario']['id']}",
        json={"bio": "invadido"},
        headers=cabecalho_comum,
    )
    assert resposta.status_code == 403


def test_usuario_edita_a_si_mesmo(cliente, cabecalho_comum):
    meu_id = _id_do_token(cliente, cabecalho_comum)
    resposta = cliente.put(
        f"/api/v1/usuarios/{meu_id}",
        json={"bio": "caçador de bugs"},
        headers=cabecalho_comum,
    )
    assert resposta.status_code == 200
    assert resposta.get_json()["bio"] == "caçador de bugs"


# --- Moderação ponta a ponta pelo HTTP ----------------------------------

def test_topico_oculto_some_da_listagem_publica(cliente, cabecalho_comum, app):
    """A lógica está testada em unidade; isto testa a FIAÇÃO em
    composicao.py — um typo na lista de services moderáveis passaria
    despercebido sem este teste."""
    from app.extensions import db
    from app.models import Topico

    cliente.post(
        "/api/v1/topicos", json={"titulo": "Some daqui"}, headers=cabecalho_comum
    )
    topico = db.session.execute(db.select(Topico)).scalars().first()
    topico.oculto = True
    db.session.commit()

    assert cliente.get("/api/v1/topicos").get_json()["total"] == 0
    assert cliente.get(f"/api/v1/topicos/{topico.id}").status_code == 404


def test_todos_os_18_recursos_respondem(cliente):
    from app.controllers.registro import RECURSOS

    assert len(RECURSOS) == 18
    for recurso in RECURSOS:
        prefixo = recurso[0]
        resposta = cliente.get(f"/api/v1/{prefixo}")
        assert resposta.status_code == 200, f"/api/v1/{prefixo} falhou"
        assert "itens" in resposta.get_json()
