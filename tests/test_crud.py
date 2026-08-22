import pytest


@pytest.fixture
def cabecalho(cliente):
    """Registra um usuário e devolve o header Authorization."""
    corpo = cliente.post(
        "/api/auth/registro",
        json={"nome_usuario": "gamer", "email": "g@l.dev", "senha": "senha123"},
    ).get_json()
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


def test_autor_e_gravado_automaticamente(cliente, cabecalho):
    jogo = cliente.post(
        "/api/v1/jogos", json={"nome": "Celeste"}, headers=cabecalho
    ).get_json()
    topico = cliente.post(
        "/api/v1/topicos",
        json={"titulo": "Dica de speedrun", "jogo_id": jogo["id"]},
        headers=cabecalho,
    ).get_json()
    assert topico["usuario_id"] is not None


def test_todos_os_18_recursos_respondem(cliente):
    from app.controllers.registro import RECURSOS

    assert len(RECURSOS) == 18
    for recurso in RECURSOS:
        prefixo = recurso[0]
        resposta = cliente.get(f"/api/v1/{prefixo}")
        assert resposta.status_code == 200, f"/api/v1/{prefixo} falhou"
        assert "itens" in resposta.get_json()
