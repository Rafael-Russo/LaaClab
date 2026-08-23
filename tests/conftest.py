import pytest

from app import create_app
from app.extensions import db as _db
from config import TestingConfig


@pytest.fixture
def app():
    aplicacao = create_app(TestingConfig)
    with aplicacao.app_context():
        _db.create_all()
        yield aplicacao
        _db.session.remove()
        _db.drop_all()


@pytest.fixture
def cliente(app):
    return app.test_client()


@pytest.fixture
def sessao(app):
    return _db.session
