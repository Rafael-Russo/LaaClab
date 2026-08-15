from whitenoise import WhiteNoise

from app import create_app
from app.config import DevConfig, ProdConfig, TestConfig


def test_estatico_e_servido_no_prefixo_web(client):
    resposta = client.get("/static/web/css/probe.css")
    assert resposta.status_code == 200
    assert b"laaclab-probe" in resposta.data


def test_static_url_path_e_o_padrao():
    aplicacao = create_app(TestConfig())
    assert aplicacao.static_url_path == "/static"


def test_whitenoise_embrulha_o_wsgi_app_fora_de_debug(monkeypatch):
    monkeypatch.setenv("SECRET_KEY", "chave-real")
    aplicacao = create_app(ProdConfig())
    assert isinstance(aplicacao.wsgi_app, WhiteNoise)


def test_whitenoise_nao_embrulha_em_debug():
    """Em dev o próprio Flask serve estáticos, com recarga imediata."""
    aplicacao = create_app(DevConfig())
    assert not isinstance(aplicacao.wsgi_app, WhiteNoise)
