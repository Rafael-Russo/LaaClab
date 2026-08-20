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
#   1. o `.env` do diretório de trabalho, achado por uma busca ascendente —
#      `find_dotenv(usecwd=True)` sobe pelos ancestrais do cwd até encontrar
#      um `.env` ou esgotar o sistema de arquivos. Como isso alcança o `.env`
#      da raiz do projeto mesmo quando se roda de um subdiretório dele (um
#      caso comum no dia a dia), o local mais específico vence primeiro;
#   2. a raiz do projeto, como fallback, para quando o processo sobe de um
#      diretório de trabalho que nada diz sobre o projeto (WSGI, systemd).
#
# Esta é a segunda vez que a ordem de leitura deste arquivo vira defeito: da
# primeira, foi ler tarde demais (parágrafo acima); desta, foi a raiz do
# projeto vencer sempre que existisse, escondendo o `.env` do diretório de
# trabalho — inclusive o `.env` de teste que `test_o_valor_do_env_chega_ate_a_config`
# cria em `tmp_path`. Ao mexer aqui de novo, rode a suíte com um `.env` de
# verdade na raiz: era o cenário em que o defeito ficava invisível.
_RAIZ_DO_PROJETO = Path(__file__).resolve().parents[1]
load_dotenv(find_dotenv(usecwd=True))
load_dotenv(_RAIZ_DO_PROJETO / ".env")


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
