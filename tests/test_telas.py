import pytest

ROTAS = [
    "/",
    "/biblioteca",
    "/bugometro",
    "/historicos",
    "/alertas",
    "/comunidade",
    "/comunidade/topico/1",
    "/jogo/1",
    "/perfil",
    "/configuracao",
]


def test_o_plano_cobre_as_dez_rotas_de_tela():
    assert len(ROTAS) == 10


@pytest.mark.parametrize("rota", ROTAS)
def test_rota_de_tela_responde_200_para_quem_esta_logado(cliente_logado, rota):
    assert cliente_logado.get(rota).status_code == 200


@pytest.mark.parametrize("rota", ROTAS)
def test_rota_de_tela_manda_anonimo_para_o_login(client, rota):
    resposta = client.get(rota)

    assert resposta.status_code == 302
    assert "/entrar" in resposta.headers["Location"]


def test_o_redirecionamento_preserva_o_destino(client):
    resposta = client.get("/biblioteca")

    assert "next=%2Fbiblioteca" in resposta.headers["Location"]


def test_topico_recebe_o_id(cliente_logado):
    """Afirma o atributo, e num id que não colide com nada na página.

    A versão anterior procurava só `b"42"` no HTML inteiro; a shell publica
    `usuarioId` e outros números, então o teste passava mesmo com o
    `data-topico-id` apagado do template.
    """
    resposta = cliente_logado.get("/comunidade/topico/4242")

    assert b'data-topico-id="4242"' in resposta.data


def test_detalhe_recebe_o_id_do_jogo(cliente_logado):
    """O id 7 do teste antigo era exatamente o do usuário da sessão."""
    resposta = cliente_logado.get("/jogo/4242")

    assert b'data-jogo-id="4242"' in resposta.data


def test_id_nao_numerico_nao_casa_com_a_rota(cliente_logado):
    assert cliente_logado.get("/jogo/abacaxi").status_code == 404
