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
RODAPE_INICIO = "<!-- CASCA:RODAPE:INICIO -->"
RODAPE_FIM = "<!-- CASCA:RODAPE:FIM -->"

GRUPOS = {
    "aplicação": [
        "inicio.html", "biblioteca.html", "bugometro.html", "jogo.html",
        "alertas.html", "comunidade.html", "perfil.html",
        "explorar.html", "configuracao.html",
    ],
    "autenticação": ["login.html", "registro.html"],
}


def extrair(caminho: Path) -> tuple[str, str]:
    """Devolve os dois blocos da casca: (topo, rodapé).

    O topo vai de CASCA:INICIO a CASCA:FIM, e o rodapé de
    CASCA:RODAPE:INICIO a CASCA:RODAPE:FIM. Entre CASCA:FIM e
    CASCA:RODAPE:INICIO fica a região de conteúdo de cada tela
    (`<main id="conteudo">` ou `<div id="conteudo">`), que não é
    comparada — é o trabalho próprio de cada página."""
    texto = caminho.read_text(encoding="utf-8")
    try:
        topo_comeco = texto.index(INICIO) + len(INICIO)
        topo_fim = texto.index(FIM)
        rodape_comeco = texto.index(RODAPE_INICIO) + len(RODAPE_INICIO)
        rodape_fim = texto.index(RODAPE_FIM)
    except ValueError:
        raise SystemExit(f"{caminho.name}: marcadores de casca ausentes.")
    return texto[topo_comeco:topo_fim], texto[rodape_comeco:rodape_fim]


def main() -> int:
    registradas = {nome for arquivos in GRUPOS.values() for nome in arquivos}
    no_disco = {caminho.name for caminho in PAGINAS.glob("*.html")}

    # Falha fechada: uma página nova que ninguém registrou aqui passaria
    # sem verificação nenhuma, e a guarda ainda diria "Casca OK." — que é
    # pior que não ter guarda, porque dá confiança falsa.
    orfas = sorted(no_disco - registradas)
    if orfas:
        print("Páginas fora de qualquer grupo em GRUPOS:")
        for nome in orfas:
            print(f"  {nome}")
        return 1

    faltando = sorted(registradas - no_disco)
    if faltando:
        print("Páginas listadas em GRUPOS que não existem no disco:")
        for nome in faltando:
            print(f"  {nome}")
        return 1

    problemas = []
    for grupo, arquivos in GRUPOS.items():
        blocos = {nome: extrair(PAGINAS / nome) for nome in arquivos}
        referencia_nome = arquivos[0]
        topo_referencia, rodape_referencia = blocos[referencia_nome]
        for nome, (topo, rodape) in blocos.items():
            if topo != topo_referencia:
                problemas.append(
                    f"  casca (topo) de {grupo}: {nome} difere de {referencia_nome}"
                )
            if rodape != rodape_referencia:
                problemas.append(
                    f"  casca (rodapé) de {grupo}: {nome} difere de {referencia_nome}"
                )
    if problemas:
        print("Casca divergente:")
        print("\n".join(problemas))
        return 1
    print("Casca OK.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
