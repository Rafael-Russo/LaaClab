import os
from pathlib import Path

from dotenv import find_dotenv, load_dotenv

# O `.env` precisa ser lido ANTES do corpo de `Config`, que consulta
# `os.environ` no momento do import. Enquanto `load_dotenv()` morava dentro de
# `create_app()`, a classe já tinha sido avaliada e o `.env` era ignorado em
# silêncio — o app subia com o `SECRET_KEY` de exemplo, publicado no
# `.env.example`. Carregar aqui, no topo do módulo, garante a ordem pela
# estrutura do arquivo, e não por convenção.
#
# Procuramos em dois lugares, nesta ordem (a primeira definição vence, porque
# `load_dotenv` não sobrescreve variável já presente no ambiente):
#   1. a raiz do projeto, ao lado de `app/` — funciona de qualquer diretório
#      de trabalho, inclusive sob WSGI;
#   2. o diretório de trabalho e seus pais — cobre quem mantém o `.env` fora
#      da árvore do código.
_RAIZ_DO_PROJETO = Path(__file__).resolve().parents[1]
load_dotenv(_RAIZ_DO_PROJETO / ".env")
load_dotenv(find_dotenv(usecwd=True))


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
