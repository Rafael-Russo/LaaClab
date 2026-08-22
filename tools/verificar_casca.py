"""Falha se as cópias da casca divergirem.

A casca é copiada em cada página por decisão de projeto: sem
`{% extends %}` e sem injeção por JS, a página chega pintada e não há
mecanismo em tempo de execução. O preço é a divergência silenciosa, e é
esta guarda que o paga.

O bloco NÃO contém o estado ativo do menu: `is-active` sai de
`<body data-tela=...>`, aplicado por `casca.js`. Isso é o que permite
comparar byte a byte em vez de aproximadamente — comparação aproximada
seria o mesmo que não ter guarda.
"""
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
PAGINAS = RAIZ / "view" / "paginas"

INICIO = "<!-- CASCA:INICIO -->"
FIM = "<!-- CASCA:FIM -->"

GRUPOS = {
    "aplicação": [
        "inicio.html", "biblioteca.html", "bugometro.html", "jogo.html",
        "alertas.html", "comunidade.html", "perfil.html",
    ],
    "autenticação": ["login.html", "registro.html"],
}


def extrair(caminho: Path) -> str:
    texto = caminho.read_text(encoding="utf-8")
    try:
        comeco = texto.index(INICIO) + len(INICIO)
        fim = texto.index(FIM)
    except ValueError:
        raise SystemExit(f"{caminho.name}: marcadores de casca ausentes.")
    return texto[comeco:fim]


def main() -> int:
    problemas = []
    for grupo, arquivos in GRUPOS.items():
        blocos = {nome: extrair(PAGINAS / nome) for nome in arquivos}
        referencia_nome = arquivos[0]
        referencia = blocos[referencia_nome]
        for nome, bloco in blocos.items():
            if bloco != referencia:
                problemas.append(
                    f"  casca de {grupo}: {nome} difere de {referencia_nome}"
                )
    if problemas:
        print("Casca divergente:")
        print("\n".join(problemas))
        return 1
    print("Casca OK.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
