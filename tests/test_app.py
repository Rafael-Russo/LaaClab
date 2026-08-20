import importlib

import pytest

import app.config
from app import create_app
from app.config import Config, TestConfig


@pytest.fixture
def ambiente_de_env():
    """Deixa o teste recarregar `app.config` sem vazar o resultado.

    `Config` lê `os.environ` no corpo da classe, então só um `importlib.reload`
    exercita a leitura do `.env`. O `MonkeyPatch.context()` é desfeito no
    teardown *antes* do reload final, devolvendo o módulo ao ambiente real —
    sem isso `app.config` ficaria com os valores do `.env` temporário.
    """
    with pytest.MonkeyPatch.context() as ambiente:
        yield ambiente
    importlib.reload(app.config)


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


def test_o_valor_do_env_chega_ate_a_config(tmp_path, ambiente_de_env):
    """Regressão: o `.env` precisa ser lido antes do corpo de `Config`.

    Enquanto `load_dotenv()` ficou em `create_app()`, a classe já havia lido
    `os.environ` no import e o arquivo era ignorado em silêncio — o app usava
    o `SECRET_KEY` de exemplo mesmo com um `.env` no lugar.
    """
    (tmp_path / ".env").write_text("API_BASE_URL=http://api-do-env.test\n", encoding="utf-8")
    ambiente_de_env.chdir(tmp_path)
    ambiente_de_env.delenv("API_BASE_URL", raising=False)

    recarregada = importlib.reload(app.config)

    assert recarregada.Config.API_BASE_URL == "http://api-do-env.test"
