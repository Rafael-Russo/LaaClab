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


def test_host_com_sufixo_apos_dois_pontos_e_rejeitado(client_com_hosts):
    """Host header injection: um host permitido seguido de ``:destino`` não
    pode passar pela allowlist enquanto ``request.host`` continua envenenado
    para quem monta URLs absolutas depois (ex.: link de reset de senha)."""
    resposta = client_com_hosts.get(
        "/healthz", headers={"Host": "laaclab.example:evil.example"}
    )
    assert resposta.status_code == 400


def test_host_com_dois_dois_pontos_e_rejeitado(client_com_hosts):
    """Host malformado (mais de um ``:``) precisa ser rejeitado, não
    remendado por um fatiamento que só olha o primeiro ou o último ``:``."""
    resposta = client_com_hosts.get(
        "/healthz", headers={"Host": "laaclab.example:8000:evil"}
    )
    assert resposta.status_code == 400


def test_host_e_comparado_sem_diferenciar_maiusculas(client_com_hosts):
    """Nomes de domínio não diferenciam maiúsculas de minúsculas."""
    resposta = client_com_hosts.get("/healthz", headers={"Host": "LaaCLab.Example"})
    assert resposta.status_code == 200


def test_host_ipv6_com_porta_e_aceito(client):
    """Literal IPv6 entre colchetes precisa ser reconhecido como um único
    host, com a porta reconhecida e descartada separadamente — fatiar no
    ``:`` quebraria isso, já que o próprio literal é cheio de ``:``."""
    config = TestConfig()
    config.ALLOWED_HOSTS = ["[::1]"]
    cliente = create_app(config).test_client()
    resposta = cliente.get("/healthz", headers={"Host": "[::1]:8000"})
    assert resposta.status_code == 200


def test_lista_vazia_desliga_a_checagem(client):
    """TestConfig usa ALLOWED_HOSTS=[]; qualquer host passa."""
    resposta = client.get("/healthz", headers={"Host": "qualquer.example"})
    assert resposta.status_code == 200
