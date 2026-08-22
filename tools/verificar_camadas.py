"""Guarda automática das camadas.

Falha se:
  - app/controllers/ tocar db.session, db.select ou importar model
  - app/services/ importar flask, flask_jwt_extended ou app.extensions
  - qualquer lugar usar a API legada Model.query
  - qualquer lugar usar datetime.utcnow (deprecado)

Uso: python tools/verificar_camadas.py
"""
import re
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent

REGRAS = [
    (
        "app/controllers",
        [
            (r"\bdb\.session\b", "Controller não pode tocar db.session"),
            (r"\bdb\.select\b", "Controller não pode montar consulta"),
            (r"from app\.models import", "Controller não pode importar model"),
            (r"from app\.repositories", "Controller não pode falar com Repository"),
        ],
    ),
    (
        "app/services",
        [
            (r"^\s*from flask", "Service não pode importar Flask"),
            (r"^\s*import flask", "Service não pode importar Flask"),
            (r"flask_jwt_extended", "Service não pode conhecer JWT"),
            (r"from app\.extensions", "Service não pode tocar extensões Flask"),
            (r"\bjsonify\b", "Service não pode montar resposta HTTP"),
            (r"\brequest\b", "Service não pode ler a requisição"),
        ],
    ),
    (
        "app",
        [
            (r"\.query\.", "Use db.select / db.session.get, não Model.query"),
            (r"datetime\.utcnow", "Use agora() de app.models.usuario"),
        ],
    ),
]


def violacoes() -> list[str]:
    achados = []
    for pasta, regras in REGRAS:
        base = RAIZ / pasta
        if not base.exists():
            continue
        for arquivo in base.rglob("*.py"):
            texto = arquivo.read_text(encoding="utf-8")
            for numero, linha in enumerate(texto.splitlines(), start=1):
                if linha.lstrip().startswith("#"):
                    continue
                for padrao, mensagem in regras:
                    if re.search(padrao, linha, flags=re.MULTILINE):
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
