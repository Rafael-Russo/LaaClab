from celery import shared_task

from app import create_app
from app.config import TestConfig
from app.extensions import db


@shared_task
def somar(a, b):
    return a + b


@shared_task
def usa_o_contexto():
    """Falharia com RuntimeError se a task rodasse fora do app context."""
    return db.session is not None


def test_celery_e_registrado_nas_extensions():
    aplicacao = create_app(TestConfig())
    assert "celery" in aplicacao.extensions


def test_celery_le_a_config_da_app():
    aplicacao = create_app(TestConfig())
    assert aplicacao.extensions["celery"].conf.task_always_eager is True


def test_task_roda_sincrona_nos_testes(app):
    assert somar.delay(2, 3).get() == 5


def test_task_roda_dentro_do_app_context(app):
    assert usa_o_contexto.delay().get() is True
