import os


class Config:
    """Configuração de runtime lida do ambiente.

    `API_BASE_URL` é a raiz da API Laravel *sem* o sufixo `/api` e sem barra
    final — quem monta a URL acrescenta `/api/<recurso>`.
    """

    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-inseguro-troque-em-producao")
    API_BASE_URL = os.environ.get("API_BASE_URL", "http://localhost:8000").rstrip("/")
    API_TIMEOUT = float(os.environ.get("API_TIMEOUT", "5"))


class TestConfig(Config):
    TESTING = True
    SECRET_KEY = "chave-de-teste"
    API_BASE_URL = "http://api.test"
    WTF_CSRF_ENABLED = False
