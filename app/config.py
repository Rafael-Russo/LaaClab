"""Configuração da aplicação Flask.

As classes são **instanciadas** (e não usadas como classes) para que as
variáveis de ambiente sejam lidas na criação do objeto, e não no import do
módulo — é isso que torna a config testável com `monkeypatch.setenv`.
`app.config.from_object` aceita instâncias e lê os atributos maiúsculos.
"""

import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent

# Conveniência de desenvolvimento, igual ao que o settings.py do Django faz.
load_dotenv(BASE_DIR / ".env")


def env_bool(name: str, default: bool = False) -> bool:
    return os.getenv(name, str(default)).strip().lower() in {"1", "true", "yes", "on"}


def env_list(name: str, default: str = "") -> list[str]:
    return [item.strip() for item in os.getenv(name, default).split(",") if item.strip()]


def normalize_database_url(url: str) -> str:
    """O SQLAlchemy exige um driver explícito na URL; o Django não exigia.

    `mysql://...` (o que está no .env e no compose hoje) vira
    `mysql+mysqldb://...`, que é o driver do mysqlclient já instalado.
    """
    prefixo = "mysql://"
    if url.startswith(prefixo):
        return "mysql+mysqldb://" + url[len(prefixo) :]
    return url


class BaseConfig:
    """Valores comuns a todos os ambientes."""

    DEBUG = False
    TESTING = False

    def __init__(self) -> None:
        self.SECRET_KEY = os.getenv("SECRET_KEY", "")

        url = os.getenv("DATABASE_URL", "")
        self.SQLALCHEMY_DATABASE_URI = (
            normalize_database_url(url) if url else f"sqlite:///{BASE_DIR / 'flask.sqlite3'}"
        )
        self.SQLALCHEMY_ENGINE_OPTIONS = {
            "pool_recycle": int(os.getenv("DB_POOL_RECYCLE", "600")),
            "pool_pre_ping": True,
        }

        self.ALLOWED_HOSTS = env_list("ALLOWED_HOSTS", "localhost,127.0.0.1")
        # Flask-WTF has no CSRF_TRUSTED_ORIGINS knob: CSRFProtect derives the
        # accepted referrer straight from request.host, so ALLOWED_HOSTS above
        # already plays that role — an origin only gets a valid referrer once
        # its host clears the allowlist.

        # Atrás de proxy: consumir X-Forwarded-* só é seguro quando há de fato
        # um proxy na frente — sem ele o cliente forja os cabeçalhos.
        self.TRUSTED_PROXY = env_bool("TRUSTED_PROXY", False)
        # Lidos do ambiente (não hardcoded): .env.example já documenta os
        # dois como knobs gerais, e um valor hardcoded aqui faria
        # SSL_REDIRECT=1 em dev não fazer nada — o mesmo formato de knob
        # morto do WTF_CSRF_TRUSTED_ORIGINS removido acima.
        self.SSL_REDIRECT = env_bool("SSL_REDIRECT", False)
        self.HSTS_SECONDS = int(os.getenv("HSTS_SECONDS", "0"))

        broker = os.getenv("CELERY_BROKER_URL", "redis://127.0.0.1:6379/0")
        self.CELERY = {
            "broker_url": broker,
            "result_backend": os.getenv("CELERY_RESULT_BACKEND", broker),
            "task_always_eager": env_bool("CELERY_TASK_ALWAYS_EAGER", False),
            "task_eager_propagates": True,
        }

        self.MAIL_SERVER = os.getenv("MAIL_SERVER", "localhost")
        self.MAIL_PORT = int(os.getenv("MAIL_PORT", "25"))
        self.MAIL_USE_TLS = env_bool("MAIL_USE_TLS", False)
        self.MAIL_USERNAME = os.getenv("MAIL_USERNAME") or None
        self.MAIL_PASSWORD = os.getenv("MAIL_PASSWORD") or None
        self.MAIL_SUPPRESS_SEND = env_bool("MAIL_SUPPRESS_SEND", True)
        self.MAIL_DEFAULT_SENDER = os.getenv("MAIL_DEFAULT_SENDER", "nao-responda@laaclab.example")

        self.VAPID_PUBLIC_KEY = os.getenv("VAPID_PUBLIC_KEY", "")
        self.VAPID_PRIVATE_KEY = os.getenv("VAPID_PRIVATE_KEY", "")
        self.VAPID_ADMIN_EMAIL = os.getenv("VAPID_ADMIN_EMAIL", "admin@laaclab.example")
        self.BUGS_CLASSIFIER = os.getenv("BUGS_CLASSIFIER", "embedding")

        # Mesmo tamanho de página do DRF (REST_FRAMEWORK["PAGE_SIZE"]) — o
        # front-end pagina contando com ele.
        self.PAGE_SIZE = int(os.getenv("PAGE_SIZE", "20"))

        # flask-smorest (a API v1 chega na fatia 1; a config já fica pronta).
        self.API_TITLE = "LaaCLab API"
        self.API_VERSION = "v1"
        self.OPENAPI_VERSION = "3.0.3"
        self.OPENAPI_URL_PREFIX = "/api/v1"
        self.OPENAPI_SWAGGER_UI_PATH = "/docs"
        self.OPENAPI_SWAGGER_UI_URL = "https://cdn.jsdelivr.net/npm/swagger-ui-dist/"


class DevConfig(BaseConfig):
    DEBUG = True

    def __init__(self) -> None:
        super().__init__()
        if not self.SECRET_KEY:
            self.SECRET_KEY = "flask-insecure-dev-only-do-not-use-in-production"


class ProdConfig(BaseConfig):
    def __init__(self) -> None:
        super().__init__()
        if not self.SECRET_KEY:
            raise RuntimeError("SECRET_KEY deve ser definida quando APP_CONFIG=prod.")
        if not self.ALLOWED_HOSTS:
            raise RuntimeError("ALLOWED_HOSTS não pode ser vazia quando APP_CONFIG=prod.")
        self.SESSION_COOKIE_SECURE = True
        self.SESSION_COOKIE_HTTPONLY = True
        self.SESSION_COOKIE_SAMESITE = "Lax"
        self.PREFERRED_URL_SCHEME = "https"
        self.TRUSTED_PROXY = env_bool("TRUSTED_PROXY", True)
        self.SSL_REDIRECT = env_bool("SSL_REDIRECT", True)
        self.HSTS_SECONDS = int(os.getenv("HSTS_SECONDS", "3600"))
        self.MAIL_SUPPRESS_SEND = env_bool("MAIL_SUPPRESS_SEND", False)


class TestConfig(BaseConfig):
    __test__ = False  # pytest não deve tentar coletar isto como caso de teste.
    TESTING = True

    def __init__(self) -> None:
        super().__init__()
        self.SECRET_KEY = "test-secret"
        self.SQLALCHEMY_DATABASE_URI = "sqlite://"  # memória
        self.SQLALCHEMY_ENGINE_OPTIONS = {}
        self.WTF_CSRF_ENABLED = False
        self.ALLOWED_HOSTS = []  # sem checagem de host nos testes
        self.CELERY = {**self.CELERY, "task_always_eager": True}
        self.BUGS_CLASSIFIER = "fake"
        self.MAIL_SUPPRESS_SEND = True  # nenhum teste pode disparar e-mail de verdade


_CONFIGS = {"dev": DevConfig, "prod": ProdConfig, "test": TestConfig}


def get_config(name: str | None = None) -> BaseConfig:
    nome = name or os.getenv("APP_CONFIG", "dev")
    if nome not in _CONFIGS:
        raise ValueError(f"APP_CONFIG inválido: {nome!r}. Use um de {sorted(_CONFIGS)}.")
    return _CONFIGS[nome]()
