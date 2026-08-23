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
IMPORTA_MODELS = r"(from\s+app\.models|import\s+app\.models|from\s+app\s+import\s+[^#]*\bmodels\b)"
IMPORTA_REPOS = r"(from\s+app\.repositories|import\s+app\.repositories|from\s+app\s+import\s+[^#]*\brepositories\b)"
IMPORTA_EXTENSIONS = r"(from\s+app\.extensions|import\s+app\.extensions|from\s+app\s+import\s+[^#]*\bextensions\b)"

# Sem prender ao nome `db`: pega db.session, banco.session e ext.db.session,
# fechando a evasão por alias (from app.extensions import db as banco).
USA_SESSAO = r"\.\s*session\b"
USA_SELECT = r"\.\s*select\s*\("
USA_PAGINATE = r"\.\s*paginate\s*\("

#: Linhas que carregam este marcador são exceções declaradas à regra de
#: sessão — desde que o ARQUIVO também esteja em EXCECOES_SESSAO abaixo.
#: Marcador na LINHA, não no arquivo: exceção por arquivo cega a guarda
#: para todo uso novo naquele arquivo, que é o oposto de vigiar. As duas
#: condições juntas (arquivo declarado + linha marcada) impedem tanto o
#: "esse arquivo pode tudo" quanto o "um comentário em qualquer lugar
#: destrava a guarda".
MARCADOR_EXCECAO = "guarda: excecao declarada"

#: Arquivos fora de app/repositories/ com permissão DECLARADA para tocar
#: db.session/db.select/db.paginate — CADA LINHA que o faz precisa, além
#: disso, carregar MARCADOR_EXCECAO (ver acima). Um arquivo aqui sem
#: nenhuma linha marcada continua 100% vigiado; só a exceção listada é
#: que passa. Cada entrada é uma decisão registrada, com o porquê.
EXCECOES_SESSAO = {
    # `flask seed`: roda fora do ciclo de request HTTP, sem Controller
    # nem Service no caminho para delegar a escrita.
    "app/seed.py",
    # Só serve arquivo estático (send_from_directory); não fala com o
    # banco hoje. Mora em app/controllers/, então sem esta entrada
    # cairia sob a regra de sessão de controllers no instante em que
    # passasse a tocar o banco — declarada aqui de antemão.
    "app/controllers/web_controller.py",
    # `additional_claims_loader` e `token_in_blocklist_loader`
    # (flask_jwt_extended, registrados em `_registrar_handlers_jwt`)
    # rodam ANTES de qualquer Service existir no request — não há
    # camada abaixo deles para delegar a consulta. Custo medido: +2
    # SELECTs em `usuarios` por requisição autenticada, porque
    # `verify_jwt_in_request` roda duas vezes (o decorator e
    # `obter_usuario_atual`).
    "app/__init__.py",
}

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
            (r"\bjsonify\b", "Service não pode montar resposta HTTP"),
            (r"\brequest\b", "Service não pode ler a requisição"),
            (USA_SESSAO, "Service não pode tocar a sessão do banco"),
            (USA_SELECT, "Service não pode montar consulta"),
            (USA_PAGINATE, "Service não pode paginar no banco"),
        ],
    ),
    (
        "app",
        [
            (r"\b[A-Z]\w*\.\s*query\b", "Use db.select / db.session.get, não Model.query"),
            (r"\butcnow\s*\(", "Use agora() de app.models.usuario"),
        ],
    ),
    (
        # Escaneado por FORA de app/controllers e app/services de propósito:
        # é a exceção que ficou invisível até aqui. Continua vigiado (não
        # apenas documentado) — a supressão é por LINHA (MARCADOR_EXCECAO),
        # não por arquivo: qualquer uso de sessão além dos dois hooks de
        # JWT marcados ainda é pego, porque não carrega o marcador.
        "app/__init__.py",
        [
            (USA_SESSAO, "Sessão fora de app/repositories (exceção declarada em EXCECOES_SESSAO)"),
            (USA_SELECT, "Consulta fora de app/repositories (exceção declarada em EXCECOES_SESSAO)"),
            (USA_PAGINATE, "Paginação fora de app/repositories (exceção declarada em EXCECOES_SESSAO)"),
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
        # `pasta` também aceita um ARQUIVO único (ex.: "app/__init__.py"),
        # para escanear a exceção do item 5 sem varrer o pacote `app`
        # inteiro em busca de sessão — o que arrastaria app/cli.py e
        # app/errors.py para dentro desta regra sem eles terem sido
        # avaliados para isso.
        arquivos = [base] if base.is_file() else sorted(base.rglob("*.py"))
        for arquivo in arquivos:
            relativo = arquivo.relative_to(RAIZ).as_posix()
            linhas_limpas = _linhas_sem_texto(arquivo)
            # Linha CRUA (com comentário) só é lida quando o arquivo está
            # declarado em EXCECOES_SESSAO — é nela, não na limpa, que
            # MARCADOR_EXCECAO mora, já que _linhas_sem_texto apaga
            # comentários antes de procurar violação.
            linhas_cruas = (
                arquivo.read_text(encoding="utf-8").splitlines()
                if relativo in EXCECOES_SESSAO
                else None
            )
            for numero, linha in enumerate(linhas_limpas, start=1):
                for padrao, mensagem in regras:
                    if not re.search(padrao, linha):
                        continue
                    if (
                        relativo in EXCECOES_SESSAO
                        and padrao in (USA_SESSAO, USA_SELECT, USA_PAGINATE)
                        and numero - 1 < len(linhas_cruas)
                        and MARCADOR_EXCECAO in linhas_cruas[numero - 1]
                    ):
                        continue
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
