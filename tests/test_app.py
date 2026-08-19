from app import create_app
from app.config import Config, TestConfig


def test_create_app_aplica_a_config_de_teste():
    app = create_app(TestConfig)

    assert app.config["TESTING"] is True
    assert app.config["API_BASE_URL"] == "http://api.test"


def test_config_padrao_traz_as_chaves_que_o_app_precisa():
    app = create_app(Config)

    assert app.config["SECRET_KEY"]
    assert app.config["API_BASE_URL"]
    assert isinstance(app.config["API_TIMEOUT"], float)


def test_api_base_url_nunca_termina_em_barra():
    app = create_app(TestConfig)

    assert not app.config["API_BASE_URL"].endswith("/")
