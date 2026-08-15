import pytest
from celery import _state, shared_task
from sqlalchemy import text

from app import create_app
from app.config import ProdConfig, TestConfig
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


def test_flask_task_abre_o_proprio_contexto():
    """Prova que quem abre o contexto é a ``FlaskTask``, e não a fixture.

    Este é o único teste do arquivo que **não** recebe a fixture ``app`` — de
    propósito. A fixture empurra um ``app_context()`` em volta de todo teste
    que a usa, então uma ``FlaskTask.__call__`` quebrada passaria despercebida
    por qualquer teste escrito como ``def test_x(app)``. Aqui não há contexto
    ativo: se a task não abrir o seu, a query estoura.
    """
    create_app(TestConfig())  # set_default() aponta o shared_task para esta app
    assert usa_o_contexto.delay().get() == 1


_estado_celery_antes_da_poluicao = []  # ponte entre os dois testes abaixo


def test_prodconfig_polui_o_default_global_do_celery(monkeypatch):
    """Reproduz o que tests/test_static.py faz sem querer: criar uma app
    ProdConfig aponta `celery._state.default_app` (process-global) para um
    Celery não-eager com um broker Redis real. Guarda o valor de antes (não
    é necessariamente `None` — pytest-flask já cria uma app de teste via
    `_push_request_context` para qualquer teste que toque `app`/`client`)
    para o teste seguinte conferir que a poluição foi desfeita. Juntos, os
    dois provam que a fixture autouse `_celery_default_restaurado`
    (tests/conftest.py) restaura o default antes do próximo teste rodar."""
    _estado_celery_antes_da_poluicao.append(_state.default_app)
    monkeypatch.setenv("SECRET_KEY", "chave-real")
    monkeypatch.setenv("ALLOWED_HOSTS", "localhost")
    aplicacao_prod = create_app(ProdConfig())
    assert _state.default_app is aplicacao_prod.extensions["celery"]
    assert _state.default_app.conf.task_always_eager is False  # a poluição é real


def test_shared_task_nao_herda_poluicao_do_teste_anterior():
    """Depende de rodar logo após `test_prodconfig_polui_o_default_global_do_celery`
    — pytest preserva a ordem de definição dentro do arquivo e não há plugin
    de ordenação aleatória instalado (ver `pip list`).

    Sem a fixture autouse `_celery_default_restaurado` (tests/conftest.py),
    `_state.default_app` continuaria apontando para a app ProdConfig do teste
    anterior: a primeira asserção abaixo estouraria, e um `.delay()` sem app
    própria tentaria uma conexão de rede de verdade em vez de rodar síncrono
    (confirmado por experimento: ``somar.delay()`` sem nenhuma app registrada
    estoura ``OperationalError`` tentando alcançar um broker AMQP local).
    Verificado por experimento: comentar a fixture faz a primeira asserção
    abaixo falhar (ver relatório).
    """
    assert _state.default_app is _estado_celery_antes_da_poluicao[0]  # já restaurado

    aplicacao = create_app(TestConfig())
    with aplicacao.app_context():
        assert somar.delay(2, 3).get(timeout=2) == 5
