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
def test_rota_de_tela_responde_200(client, rota):
    assert client.get(rota).status_code == 200


def test_thread_recebe_o_id_do_topico(client):
    assert b"42" in client.get("/comunidade/topico/42").data


def test_detalhe_recebe_o_id_do_jogo(client):
    assert b"7" in client.get("/jogo/7").data


def test_id_nao_numerico_nao_casa_com_a_rota(client):
    assert client.get("/jogo/abacaxi").status_code == 404
