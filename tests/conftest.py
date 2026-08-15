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
    # Atenção: isto empurra um app context em volta de todo teste que usa a
    # fixture. É conveniente, mas mascara qualquer código que deveria abrir o
    # contexto sozinho — uma `FlaskTask` quebrada passaria despercebida. Teste
    # que queira provar *quem* abre o contexto não pode usar esta fixture.
    with aplicacao.app_context():
        yield aplicacao


@pytest.fixture
def client(app):
    return app.test_client()
