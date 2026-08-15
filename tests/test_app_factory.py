from app import create_app
from app.config import TestConfig
from app.extensions import db


def test_create_app_devolve_uma_app_configurada():
    aplicacao = create_app(TestConfig())
    assert aplicacao.config["TESTING"] is True
    assert aplicacao.config["SQLALCHEMY_DATABASE_URI"] == "sqlite://"


def test_create_app_registra_as_extensions():
    aplicacao = create_app(TestConfig())
    for chave in ("sqlalchemy", "migrate", "csrf"):
        assert chave in aplicacao.extensions


def test_login_manager_esta_vinculado():
    """``login_manager is not None`` nunca falharia: é o mesmo objeto
    global de app/extensions.py, vinculado ou não. O que a fatia 0 (Task 3)
    quebrou de verdade foi esquecer o ``user_loader`` — o guardião correto é
    o próprio callback registrado."""
    aplicacao = create_app(TestConfig())
    assert aplicacao.login_manager._user_callback is not None


def test_swagger_ui_responde(client):
    """flask-smorest montado em /api/v1 — ainda sem nenhum recurso."""
    resposta = client.get("/api/v1/docs")
    assert resposta.status_code == 200


def test_openapi_json_e_servido(client):
    resposta = client.get("/api/v1/openapi.json")
    assert resposta.status_code == 200
    assert resposta.get_json()["info"]["title"] == "LaaCLab API"


def test_duas_apps_nao_compartilham_config():
    """A factory não pode vazar estado entre instâncias."""
    uma = create_app(TestConfig())
    outra = create_app(TestConfig())
    uma.config["MARCADOR"] = 1
    assert "MARCADOR" not in outra.config


def test_healthz_responde_ok(client):
    resposta = client.get("/healthz")
    assert resposta.status_code == 200
    assert resposta.get_json() == {"status": "ok"}


def test_db_tem_sessao_no_contexto_da_app(app):
    assert db.session is not None
