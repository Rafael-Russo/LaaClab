import pytest
from celery import shared_task
from sqlalchemy import text

from app import create_app
from app.config import TestConfig
from app.extensions import db


@shared_task
def somar(a, b):
    return a + b


@shared_task
def usa_o_contexto():
    """Executa uma query — o que exige o app context estar aberto.

    Cuidado: ``db.session is not None`` **não** serviria aqui. No
    Flask-SQLAlchemy 3.1 a session é um ``scoped_session`` construído junto com
    o objeto ``SQLAlchemy``, então ler o atributo passa fora de qualquer
    contexto. Já executar a query obriga a resolver o engine via
    ``current_app.extensions``, que só existe dentro do contexto.
    """
    return db.session.execute(text("SELECT 1")).scalar()


def test_celery_e_registrado_nas_extensions():
    aplicacao = create_app(TestConfig())
    assert "celery" in aplicacao.extensions


def test_celery_le_a_config_da_app():
    aplicacao = create_app(TestConfig())
    assert aplicacao.extensions["celery"].conf.task_always_eager is True


def test_task_roda_sincrona_nos_testes(app):
    assert somar.delay(2, 3).get() == 5


def test_task_roda_dentro_do_app_context(app):
    assert usa_o_contexto.delay().get() == 1


def test_a_task_realmente_depende_do_contexto():
    """Guarda do teste acima, para ele não virar verde por acidente.

    ``run()`` chama a função crua, pulando o ``__call__`` da ``FlaskTask`` —
    que é justamente quem abre o contexto. Se isto **não** estourar, o teste
    anterior deixou de medir o que promete.
    """
    with pytest.raises(RuntimeError):
        usa_o_contexto.run()
