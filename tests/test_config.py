import pytest

from app.config import (
    DevConfig,
    ProdConfig,
    TestConfig,
    env_bool,
    env_list,
    get_config,
    normalize_database_url,
)


@pytest.mark.parametrize("valor", ["1", "true", "TRUE", "yes", "on"])
def test_env_bool_aceita_valores_verdadeiros(monkeypatch, valor):
    monkeypatch.setenv("X_FLAG", valor)
    assert env_bool("X_FLAG") is True


@pytest.mark.parametrize("valor", ["0", "false", "no", "off", ""])
def test_env_bool_aceita_valores_falsos(monkeypatch, valor):
    monkeypatch.setenv("X_FLAG", valor)
    assert env_bool("X_FLAG") is False


def test_env_bool_usa_default_quando_ausente(monkeypatch):
    monkeypatch.delenv("X_FLAG", raising=False)
    assert env_bool("X_FLAG", True) is True


def test_env_list_separa_e_limpa(monkeypatch):
    monkeypatch.setenv("X_HOSTS", " a.com , b.com ,, ")
    assert env_list("X_HOSTS") == ["a.com", "b.com"]


def test_normalize_database_url_adiciona_driver_do_mysql():
    entrada = "mysql://user:pass@db:3306/laaclab"
    assert normalize_database_url(entrada) == "mysql+mysqldb://user:pass@db:3306/laaclab"


def test_normalize_database_url_preserva_url_ja_com_driver():
    entrada = "mysql+mysqldb://user:pass@db:3306/laaclab"
    assert normalize_database_url(entrada) == entrada


def test_normalize_database_url_preserva_sqlite():
    assert normalize_database_url("sqlite:///x.db") == "sqlite:///x.db"


def test_dev_config_cai_para_sqlite_sem_database_url(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    cfg = DevConfig()
    assert cfg.SQLALCHEMY_DATABASE_URI.startswith("sqlite:///")
    assert cfg.DEBUG is True


def test_dev_config_tolera_secret_key_ausente(monkeypatch):
    monkeypatch.delenv("SECRET_KEY", raising=False)
    assert DevConfig().SECRET_KEY  # default inseguro, mas presente


def test_dev_config_usa_pool_recycle_default_quando_ausente(monkeypatch):
    monkeypatch.delenv("DB_POOL_RECYCLE", raising=False)
    cfg = DevConfig()
    assert cfg.SQLALCHEMY_ENGINE_OPTIONS["pool_recycle"] == 600


def test_dev_config_usa_pool_recycle_do_ambiente(monkeypatch):
    monkeypatch.setenv("DB_POOL_RECYCLE", "120")
    cfg = DevConfig()
    assert cfg.SQLALCHEMY_ENGINE_OPTIONS["pool_recycle"] == 120


def test_prod_config_exige_secret_key(monkeypatch):
    monkeypatch.delenv("SECRET_KEY", raising=False)
    with pytest.raises(RuntimeError, match="SECRET_KEY"):
        ProdConfig()


def test_prod_config_aceita_secret_key_do_ambiente(monkeypatch):
    monkeypatch.setenv("SECRET_KEY", "chave-real")
    cfg = ProdConfig()
    assert cfg.SECRET_KEY == "chave-real"
    assert cfg.DEBUG is False
    assert cfg.SESSION_COOKIE_SECURE is True


def test_test_config_usa_sqlite_em_memoria_e_celery_sincrono():
    cfg = TestConfig()
    assert cfg.SQLALCHEMY_DATABASE_URI == "sqlite://"
    assert cfg.TESTING is True
    assert cfg.WTF_CSRF_ENABLED is False
    assert cfg.CELERY["task_always_eager"] is True


def test_get_config_resolve_pelo_ambiente(monkeypatch):
    monkeypatch.setenv("APP_CONFIG", "test")
    assert isinstance(get_config(), TestConfig)


def test_get_config_default_e_dev(monkeypatch):
    monkeypatch.delenv("APP_CONFIG", raising=False)
    assert isinstance(get_config(), DevConfig)


def test_get_config_rejeita_nome_desconhecido():
    with pytest.raises(ValueError, match="APP_CONFIG"):
        get_config("inexistente")
