"""Fixtures compartilhadas da suíte Flask.

Cresce a cada fatia: aqui entram só as fixtures que não dependem de model
algum. `db`, `client` e os clientes autenticados chegam nas tasks seguintes.
"""

import pytest

from app import create_app
from app.config import TestConfig


@pytest.fixture
def app():
    aplicacao = create_app(TestConfig())
    with aplicacao.app_context():
        yield aplicacao


@pytest.fixture
def client(app):
    return app.test_client()
