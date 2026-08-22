"""Rótulos em português para os valores de enum do domínio.

O JS renderiza o texto que vier, sem traduzir nada: uma chave sem rótulo
aparece crua na tela. Ficam aqui, e não no model, porque são vocabulário
de apresentação — o model guarda a chave.
"""

CATEGORIAS = {
    "crash": "Crash",
    "graficos": "Gráficos",
    "progressao": "Progressão",
    "desempenho": "Desempenho",
    "online": "Online",
    "outro": "Outro",
}

SEVERIDADES = {
    "baixa": "Baixa",
    "media": "Média",
    "alta": "Alta",
    "critica": "Crítica",
}

CATEGORIA_PADRAO = "Outro"
SEVERIDADE_PADRAO = "Média"


def rotulo_categoria(chave: str) -> str:
    return CATEGORIAS.get(chave, CATEGORIA_PADRAO)


def rotulo_severidade(chave: str) -> str:
    return SEVERIDADES.get(chave, SEVERIDADE_PADRAO)
