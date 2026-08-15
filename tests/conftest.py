"""Fixtures compartilhadas da suíte Flask.

Cresce a cada fatia: aqui entram só as fixtures que não dependem de model
algum. `db`, `client` e os clientes autenticados chegam nas tasks seguintes.
"""

import pytest

from app import create_app
from app.config import TestConfig


@pytest.fixture(autouse=True)
def _celery_default_restaurado():
    """Restaura o default global do Celery depois de cada teste.

    ``celery_init_app`` chama ``set_default()``, que é process-global: um teste
    que cria uma app com outra config deixa o default apontando para ela, e o
    próximo ``task.delay()`` roda com a config errada — inclusive tentando
    alcançar um broker real. Cada app tem seu próprio engine e, em
    ``sqlite://``, seu próprio banco em memória, então o sintoma aparece como
    dado sumido, não como erro de configuração.
    """
    from celery import _state

    anterior = _state.default_app
    yield
    _state.default_app = anterior


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
