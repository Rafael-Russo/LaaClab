import pytest
import responses

from app import create_app
from app.config import TestConfig

USUARIO_DE_TESTE = {"id": 7, "nome_usuario": "Nikola98", "nivel": 12, "avatar_url": None}


@pytest.fixture
def app():
    return create_app(TestConfig)


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def cliente_logado(client):
    """Cliente com sessão aberta, sem tocar na rede: o login vai para um mock."""
    with responses.RequestsMock() as mock:
        mock.post("http://api.test/api/login", json=USUARIO_DE_TESTE, status=200)
        client.post("/entrar", data={"email": "nikola@exemplo.com", "senha": "segredo"})
    return client
