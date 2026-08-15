"""Fixtures compartilhadas da suíte Flask.

Cresce a cada fatia: aqui entram só as fixtures que não dependem de model
algum. `db`, `client` e os clientes autenticados chegam nas tasks seguintes.
"""

import pytest

# Importa o agregador para registrar TODOS os models no metadata antes do
# `create_all()` abaixo. Sem isto, `create_all` só cria as tabelas dos models
# que o arquivo de teste em execução tiver importado por acaso: rodar um teste
# isolado que renderize template sem importar `app.core.models` deixa a tabela
# `module` de fora e o context processor quebra com "no such table".
import app.models  # noqa: F401
from app import create_app
from app.config import TestConfig
from app.extensions import db


@pytest.fixture(autouse=True)
def _celery_default_restaurado():
    """Restaura o default global do Celery depois de cada teste.

    ``celery_init_app`` chama ``set_default()``, que é process-global: um teste
    que cria uma app com outra config deixa o default apontando para ela, e o
    próximo ``task.delay()`` roda com a config errada — inclusive tentando
    alcançar um broker real. Cada app tem seu próprio engine e, em
    ``sqlite://``, seu próprio banco em memória, então o sintoma aparece como
    dado sumido, não como erro de configuração.

    Restaurar só ``_state.default_app`` não basta: ``_get_current_app()`` lê
    ``_tls.current_app or default_app`` (``celery/_state.py``), e o
    thread-local domina — ``Celery.__init__`` com o ``set_as_current=True``
    padrão o grava via ``_set_current_app()``. É exatamente por ele que o
    proxy do ``shared_task`` resolve. Restaurar só o global deixa o
    thread-local no comando e a fixture não faz nada.
    """
    from celery import _state

    anterior = (_state.default_app, getattr(_state._tls, "current_app", None))
    yield
    _state.default_app, _state._tls.current_app = anterior


@pytest.fixture
def app():
    aplicacao = create_app(TestConfig())
    # Atenção: isto empurra um app context em volta de todo teste que usa a
    # fixture. É conveniente, mas mascara qualquer código que deveria abrir o
    # contexto sozinho — uma `FlaskTask` quebrada passaria despercebida. Teste
    # que queira provar *quem* abre o contexto não pode usar esta fixture.
    with aplicacao.app_context():
        db.create_all()
        yield aplicacao
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()
