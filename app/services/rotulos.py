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


TIPOS_TOPICO = {
    "discussao": "Discussão",
    "bug": "Bug",
    "dica": "Dica",
    "noticia": "Notícia",
}

#: Tipo → classe CSS do badge. Os valores ficam em inglês porque são
#: sufixo de `.badge--`, igual ao `nivel` dos alertas.
NIVEIS_TOPICO = {
    "discussao": "discussion",
    "bug": "warning",
    "dica": "stable",
    "noticia": "info",
}

TIPO_PADRAO = "Discussão"
NIVEL_TIPO_PADRAO = "discussion"

#: nível de alerta → rótulo em português, capitalização normal (não caixa
#: alta). Fonte única para `AlertaService.apresentar` (card) e para o
#: resumo de `/telas/alertas` (chip): duas tabelas divergindo em
#: capitalização foi o defeito 8 da revisão de `feat/endpoints-de-tela`.
#:
#: Não confundir com `JogoService.status_para`, que repete "Crítico" e
#: "Instável" para as mesmas chaves. É outro eixo — estabilidade do
#: bugômetro, cujo `stable` é "Estável" e não "Atualização" — então as
#: duas tabelas coincidem em dois rótulos por acaso, não por serem a
#: mesma coisa.
ROTULOS_NIVEL_ALERTA = {
    "critical": "Crítico",
    "warning": "Instável",
    "stable": "Atualização",
}


def rotulo_tipo(chave: str) -> str:
    return TIPOS_TOPICO.get(chave, TIPO_PADRAO)


def nivel_tipo(chave: str) -> str:
    return NIVEIS_TOPICO.get(chave, NIVEL_TIPO_PADRAO)
