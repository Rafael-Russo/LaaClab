import pytest

from app import create_app
from app.config import TestConfig


@pytest.fixture
def client_com_hosts():
    config = TestConfig()
    config.ALLOWED_HOSTS = ["laaclab.example", "localhost"]
    return create_app(config).test_client()


def test_host_permitido_passa(client_com_hosts):
    resposta = client_com_hosts.get("/healthz", headers={"Host": "laaclab.example"})
    assert resposta.status_code == 200


def test_host_com_porta_e_comparado_sem_a_porta(client_com_hosts):
    resposta = client_com_hosts.get("/healthz", headers={"Host": "laaclab.example:8000"})
    assert resposta.status_code == 200


def test_host_desconhecido_e_rejeitado(client_com_hosts):
    resposta = client_com_hosts.get("/healthz", headers={"Host": "atacante.example"})
    assert resposta.status_code == 400


def test_lista_vazia_desliga_a_checagem(client):
    """TestConfig usa ALLOWED_HOSTS=[]; qualquer host passa."""
    resposta = client.get("/healthz", headers={"Host": "qualquer.example"})
    assert resposta.status_code == 200
