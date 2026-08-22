"""Configuração por ambiente, escolhida por FLASK_ENV."""
import os
from datetime import timedelta
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")


class BaseConfig:
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key")
    JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "dev-jwt-secret")

    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {"pool_pre_ping": True}

    JWT_ACCESS_TOKEN_EXPIRES = timedelta(
        minutes=int(os.getenv("JWT_ACCESS_MINUTOS", "30"))
    )
    JWT_REFRESH_TOKEN_EXPIRES = timedelta(
        days=int(os.getenv("JWT_REFRESH_DIAS", "7"))
    )


class DevelopmentConfig(BaseConfig):
    DEBUG = True
    _sqlite = os.getenv("SQLITE_PATH", "laac_lab.db")
    SQLALCHEMY_DATABASE_URI = f"sqlite:///{(BASE_DIR / _sqlite).as_posix()}"


class ProductionConfig(BaseConfig):
    DEBUG = False
    _u = os.getenv("MYSQL_USER", "root")
    _p = os.getenv("MYSQL_PASSWORD", "")
    _h = os.getenv("MYSQL_HOST", "localhost")
    _port = os.getenv("MYSQL_PORT", "3306")
    _db = os.getenv("MYSQL_DB", "laac_lab")
    SQLALCHEMY_DATABASE_URI = (
        f"mysql+pymysql://{_u}:{_p}@{_h}:{_port}/{_db}?charset=utf8mb4"
    )


class TestingConfig(BaseConfig):
    TESTING = True
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"


_MAPA = {
    "development": DevelopmentConfig,
    "production": ProductionConfig,
    "testing": TestingConfig,
}

TAMANHO_MINIMO_CHAVE = 32


def _exigir_chaves_fortes() -> None:
    """Falha na subida, não em produção silenciosa.

    O default de `JWT_SECRET_KEY` está no código-fonte deste repositório:
    subir em produção sem sobrescrevê-lo significa que qualquer pessoa
    que leia o repo forja um token válido. E 32 bytes é o mínimo do
    HMAC-SHA256; abaixo disso a própria PyJWT avisa.
    """
    fracas = [
        nome
        for nome in ("SECRET_KEY", "JWT_SECRET_KEY")
        if len(os.getenv(nome, "").encode("utf-8")) < TAMANHO_MINIMO_CHAVE
    ]
    if fracas:
        raise RuntimeError(
            "FLASK_ENV=production exige "
            + " e ".join(fracas)
            + f" com ao menos {TAMANHO_MINIMO_CHAVE} bytes. Gere com:\n"
            '  python -c "import secrets; print(secrets.token_urlsafe(48))"'
        )


def get_config():
    ambiente = os.getenv("FLASK_ENV", "development").lower()
    if ambiente == "production":
        _exigir_chaves_fortes()
    return _MAPA.get(ambiente, DevelopmentConfig)
