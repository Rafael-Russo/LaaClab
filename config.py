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

    POR_PAGINA_PADRAO = 20


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


def get_config():
    return _MAPA.get(os.getenv("FLASK_ENV", "development").lower(), DevelopmentConfig)
