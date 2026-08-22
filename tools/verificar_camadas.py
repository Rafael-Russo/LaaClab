"""Guarda automática das camadas.

Falha se:
  - app/controllers/ tocar sessão/consulta ou importar model/repository
  - app/services/ importar flask, app.extensions ou tocar sessão/consulta
  - qualquer lugar usar a API legada Model.query
  - qualquer lugar usar utcnow (deprecado)

Strings e comentários são apagados antes da varredura: sem isso, uma
docstring que MENCIONA db.session viraria violação — e várias docstrings
deste projeto fazem exatamente isso ao explicar a regra que respeitam.

Uso: python tools/verificar_camadas.py
"""
import io
import re
import sys
import tokenize
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent

# Cobrem submódulo (from app.models.jogo import X), import puro
# (import app.models) e a forma from app import models.
IMPORTA_MODELS = r"(from\s+app\.models|import\s+app\.models|from\s+app\s+import\s+[^#]*models)"
IMPORTA_REPOS = r"(from\s+app\.repositories|import\s+app\.repositories|from\s+app\s+import\s+[^#]*repositories)"
IMPORTA_EXTENSIONS = r"(from\s+app\.extensions|import\s+app\.extensions|from\s+app\s+import\s+[^#]*extensions)"

# Sem prender ao nome `db`: pega db.session, banco.session e ext.db.session,
# fechando a evasão por alias (from app.extensions import db as banco).
USA_SESSAO = r"\.\s*session"
USA_SELECT = r"\.\s*select\s*\("
USA_PAGINATE = r"\.\s*paginate\s*\("

REGRAS = [
    (
        "app/controllers",
        [
            (USA_SESSAO, "Controller não pode tocar a sessão do banco"),
            (USA_SELECT, "Controller não pode montar consulta"),
            (USA_PAGINATE, "Controller não pode paginar no banco"),
            (IMPORTA_MODELS, "Controller não pode importar model"),
            (IMPORTA_REPOS, "Controller não pode falar com Repository"),
        ],
    ),
    (
        "app/services",
        [
            (r"^\s*from\s+flask", "Service não pode importar Flask"),
            (r"^\s*import\s+flask", "Service não pode importar Flask"),
            (r"flask_jwt_extended", "Service não pode conhecer JWT"),
            (IMPORTA_EXTENSIONS, "Service não pode tocar extensões Flask"),
            (r"jsonify", "Service não pode montar resposta HTTP"),
            (r"request", "Service não pode ler a requisição"),
            (USA_SESSAO, "Service não pode tocar a sessão do banco"),
            (USA_SELECT, "Service não pode montar consulta"),
            (USA_PAGINATE, "Service não pode paginar no banco"),
        ],
    ),
    (
        "app",
        [
            (r"[A-Z]\w*\.\s*query", "Use db.select / db.session.get, não Model.query"),
            (r"utcnow\s*\(", "Use agora() de app.models.usuario"),
        ],
    ),
]


def _linhas_sem_texto(caminho: Path) -> list[str]:
    """Linhas do arquivo com strings e comentários substituídos por espaços.

    Preserva colunas para que o número de linha do achado continue certo.
    """
    bruto = caminho.read_text(encoding="utf-8")
    linhas = bruto.splitlines()
    try:
        tokens = list(tokenize.generate_tokens(io.StringIO(bruto).readline))
    except (tokenize.TokenError, IndentationError, SyntaxError):
        # Arquivo em edição: varrer o texto cru é melhor que não varrer.
        return linhas

    for token in tokens:
        if token.type not in (tokenize.STRING, tokenize.COMMENT):
            continue
        (linha_ini, col_ini), (linha_fim, col_fim) = token.start, token.end
        for numero in range(linha_ini, linha_fim + 1):
            indice = numero - 1
            if indice >= len(linhas):
                continue
            atual = linhas[indice]
            inicio = col_ini if numero == linha_ini else 0
            fim = col_fim if numero == linha_fim else len(atual)
            linhas[indice] = atual[:inicio] + " " * (fim - inicio) + atual[fim:]
    return linhas


def violacoes() -> list[str]:
    achados = []
    for pasta, regras in REGRAS:
        base = RAIZ / pasta
        if not base.exists():
            continue
        for arquivo in sorted(base.rglob("*.py")):
            for numero, linha in enumerate(_linhas_sem_texto(arquivo), start=1):
                for padrao, mensagem in regras:
                    if re.search(padrao, linha):
                        relativo = arquivo.relative_to(RAIZ).as_posix()
                        achados.append(f"{relativo}:{numero}: {mensagem} -> {linha.strip()}")
    return achados


def main() -> int:
    achados = violacoes()
    if achados:
        print("VIOLACOES DE CAMADA:")
        for achado in achados:
            print("  " + achado)
        return 1
    print("Camadas OK.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
