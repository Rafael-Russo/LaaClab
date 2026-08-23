"""Trocar a senha tem que derrubar as sessões antigas.

JWT não se revoga sozinho: sem uma marca no usuário, o refresh de 7 dias
já emitido continua valendo. Quem troca a senha porque ela vazou seguiria
com o invasor dentro por uma semana.
"""


def _registrar(cliente, nome="alguem"):
    return cliente.post(
        "/api/auth/registro",
        json={"nome_usuario": nome, "email": f"{nome}@l.dev", "senha": "senhaantiga1"},
    ).get_json()


def test_troca_de_senha_devolve_tokens_novos(cliente):
    dados = _registrar(cliente)
    cabecalho = {"Authorization": f"Bearer {dados['token_acesso']}"}
    resposta = cliente.post(
        "/api/auth/senha",
        headers=cabecalho,
        json={"senha_atual": "senhaantiga1", "senha_nova": "senhanova12345"},
    )
    assert resposta.status_code == 200
    corpo = resposta.get_json()
    assert corpo["token_acesso"] and corpo["token_renovacao"]


def test_senha_atual_errada_e_422_no_campo(cliente):
    """A pessoa está autenticada: é problema de campo de formulário,
    e é onde o contrato de erro põe o 422."""
    dados = _registrar(cliente)
    cabecalho = {"Authorization": f"Bearer {dados['token_acesso']}"}
    resposta = cliente.post(
        "/api/auth/senha",
        headers=cabecalho,
        json={"senha_atual": "chuteichutei", "senha_nova": "senhanova12345"},
    )
    assert resposta.status_code == 422
    assert "senha_atual" in resposta.get_json()["erros"]


def test_a_senha_nova_passa_a_valer(cliente):
    dados = _registrar(cliente)
    cabecalho = {"Authorization": f"Bearer {dados['token_acesso']}"}
    cliente.post(
        "/api/auth/senha",
        headers=cabecalho,
        json={"senha_atual": "senhaantiga1", "senha_nova": "senhanova12345"},
    )
    assert cliente.post(
        "/api/auth/login",
        json={"identificador": "alguem", "senha": "senhanova12345"},
    ).status_code == 200
    assert cliente.post(
        "/api/auth/login",
        json={"identificador": "alguem", "senha": "senhaantiga1"},
    ).status_code == 401


def test_refresh_antigo_para_de_valer(cliente):
    """O ponto todo do recurso. Sem isto, trocar a senha porque ela
    vazou deixaria o invasor dentro por mais sete dias."""
    dados = _registrar(cliente)
    refresh_antigo = dados["token_renovacao"]
    cabecalho = {"Authorization": f"Bearer {dados['token_acesso']}"}
    cliente.post(
        "/api/auth/senha",
        headers=cabecalho,
        json={"senha_atual": "senhaantiga1", "senha_nova": "senhanova12345"},
    )
    resposta = cliente.post(
        "/api/auth/renovar", headers={"Authorization": f"Bearer {refresh_antigo}"}
    )
    assert resposta.status_code == 401


def test_os_tokens_novos_continuam_valendo(cliente):
    """O corte é por instante de emissão, e os tokens devolvidos pela
    própria troca nascem no mesmo segundo. Se o corte for estrito demais,
    a pessoa é expulsa no exato momento em que se protegeu."""
    dados = _registrar(cliente)
    cabecalho = {"Authorization": f"Bearer {dados['token_acesso']}"}
    novos = cliente.post(
        "/api/auth/senha",
        headers=cabecalho,
        json={"senha_atual": "senhaantiga1", "senha_nova": "senhanova12345"},
    ).get_json()

    assert cliente.get(
        "/api/v1/eu", headers={"Authorization": f"Bearer {novos['token_acesso']}"}
    ).status_code == 200
    assert cliente.post(
        "/api/auth/renovar",
        headers={"Authorization": f"Bearer {novos['token_renovacao']}"},
    ).status_code == 200


def test_sem_token_responde_401(cliente):
    assert cliente.post(
        "/api/auth/senha",
        json={"senha_atual": "x", "senha_nova": "y"},
    ).status_code == 401


def test_revogacao_nao_depende_do_relogio(cliente):
    """A troca e o token novo nascem no MESMO segundo. Se a revogação
    comparasse instantes, ou o token velho sobreviveria ou o novo
    morreria — não existe granularidade de segundo que separe os dois."""
    dados = _registrar(cliente, "mesmosegundo")
    refresh_antigo = dados["token_renovacao"]
    cabecalho = {"Authorization": f"Bearer {dados['token_acesso']}"}

    novos = cliente.post(
        "/api/auth/senha",
        headers=cabecalho,
        json={"senha_atual": "senhaantiga1", "senha_nova": "senhanova12345"},
    ).get_json()

    # O velho morre...
    assert cliente.post(
        "/api/auth/renovar",
        headers={"Authorization": f"Bearer {refresh_antigo}"},
    ).status_code == 401
    # ...e o novo vive, no mesmo segundo.
    assert cliente.post(
        "/api/auth/renovar",
        headers={"Authorization": f"Bearer {novos['token_renovacao']}"},
    ).status_code == 200
