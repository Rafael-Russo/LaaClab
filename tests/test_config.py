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


def test_base_config_ssl_redirect_e_hsts_desligados_por_default(monkeypatch):
    monkeypatch.delenv("SSL_REDIRECT", raising=False)
    monkeypatch.delenv("HSTS_SECONDS", raising=False)
    cfg = DevConfig()
    assert cfg.SSL_REDIRECT is False
    assert cfg.HSTS_SECONDS == 0


def test_base_config_le_ssl_redirect_e_hsts_do_ambiente(monkeypatch):
    """Antes desta fix eram hardcoded em BaseConfig: SSL_REDIRECT=1 fora de
    prod não fazia nada — o mesmo formato de knob morto que a remoção do
    WTF_CSRF_TRUSTED_ORIGINS já tinha corrigido em outro lugar."""
    monkeypatch.setenv("SSL_REDIRECT", "1")
    monkeypatch.setenv("HSTS_SECONDS", "120")
    cfg = DevConfig()
    assert cfg.SSL_REDIRECT is True
    assert cfg.HSTS_SECONDS == 120


def test_prod_config_exige_secret_key(monkeypatch):
    monkeypatch.delenv("SECRET_KEY", raising=False)
    with pytest.raises(RuntimeError, match="SECRET_KEY"):
        ProdConfig()


def test_prod_config_aceita_secret_key_do_ambiente(monkeypatch):
    monkeypatch.setenv("SECRET_KEY", "chave-real")
    monkeypatch.setenv("ALLOWED_HOSTS", "laaclab.example")
    cfg = ProdConfig()
    assert cfg.SECRET_KEY == "chave-real"
    assert cfg.DEBUG is False
    assert cfg.SESSION_COOKIE_SECURE is True


def test_prod_config_exige_allowed_hosts(monkeypatch):
    """``ALLOWED_HOSTS=`` (presente e vazia) faz `env_list` devolver `[]`, o
    que desliga a checagem de Host para toda requisição — o equivalente
    Django (``DEBUG=False`` com ``ALLOWED_HOSTS`` vazia) rejeita tudo em vez
    de aceitar tudo."""
    monkeypatch.setenv("SECRET_KEY", "chave-real")
    monkeypatch.setenv("ALLOWED_HOSTS", "")
    with pytest.raises(RuntimeError, match="ALLOWED_HOSTS"):
        ProdConfig()


def test_prod_config_aceita_allowed_hosts_do_ambiente(monkeypatch):
    monkeypatch.setenv("SECRET_KEY", "chave-real")
    monkeypatch.setenv("ALLOWED_HOSTS", "laaclab.example")
    cfg = ProdConfig()
    assert cfg.ALLOWED_HOSTS == ["laaclab.example"]


def test_base_config_usa_defaults_de_mail(monkeypatch):
    for nome in ("MAIL_SERVER", "MAIL_PORT", "MAIL_USE_TLS", "MAIL_USERNAME", "MAIL_PASSWORD"):
        monkeypatch.delenv(nome, raising=False)
    cfg = DevConfig()
    assert cfg.MAIL_SERVER == "localhost"
    assert cfg.MAIL_PORT == 25
    assert cfg.MAIL_USE_TLS is False
    assert cfg.MAIL_USERNAME is None
    assert cfg.MAIL_PASSWORD is None
    assert cfg.MAIL_SUPPRESS_SEND is True  # default fora de prod: suprime


def test_base_config_le_mail_do_ambiente(monkeypatch):
    monkeypatch.setenv("MAIL_SERVER", "smtp.example.com")
    monkeypatch.setenv("MAIL_PORT", "587")
    monkeypatch.setenv("MAIL_USE_TLS", "1")
    monkeypatch.setenv("MAIL_USERNAME", "user")
    monkeypatch.setenv("MAIL_PASSWORD", "senha")
    cfg = DevConfig()
    assert cfg.MAIL_SERVER == "smtp.example.com"
    assert cfg.MAIL_PORT == 587
    assert cfg.MAIL_USE_TLS is True
    assert cfg.MAIL_USERNAME == "user"
    assert cfg.MAIL_PASSWORD == "senha"


def test_prod_config_mail_suppress_send_default_e_falso(monkeypatch):
    monkeypatch.setenv("SECRET_KEY", "chave-real")
    monkeypatch.setenv("ALLOWED_HOSTS", "laaclab.example")
    monkeypatch.delenv("MAIL_SUPPRESS_SEND", raising=False)
    assert ProdConfig().MAIL_SUPPRESS_SEND is False


def test_test_config_forca_mail_suppress_send(monkeypatch):
    """Nenhum teste pode disparar e-mail de verdade, mesmo que o ambiente
    diga o contrário."""
    monkeypatch.setenv("MAIL_SUPPRESS_SEND", "0")
    assert TestConfig().MAIL_SUPPRESS_SEND is True


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
