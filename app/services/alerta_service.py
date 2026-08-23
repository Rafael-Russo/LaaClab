"""Apresentação do alerta: severidade → rótulo, nível e ícone."""
from app.services.base import ServicoBase
from app.services.rotulos import ROTULOS_NIVEL_ALERTA

#: severidade → (rótulo exibido, nível CSS, ícone)
#: ATENÇÃO: 'atualizacao' vira nível 'stable', não 'update'. Não existe
#: classe .badge--update no CSS — emitir 'update' deixa o selo sem cor.
#: O rótulo vem de `ROTULOS_NIVEL_ALERTA` — mesma fonte que o resumo de
#: `/telas/alertas` usa, para as duas apresentações nunca divergirem.
APRESENTACAO = {
    "critica": (ROTULOS_NIVEL_ALERTA["critical"], "critical", "wifi"),
    "instavel": (ROTULOS_NIVEL_ALERTA["warning"], "warning", "alert"),
    "atualizacao": (ROTULOS_NIVEL_ALERTA["stable"], "stable", "check"),
}

FALLBACK = (ROTULOS_NIVEL_ALERTA["critical"], "critical", "wifi")


class AlertaService(ServicoBase):
    campo_dono = None

    @staticmethod
    def apresentar(alerta) -> dict:
        rotulo, nivel, icone = APRESENTACAO.get(alerta.severidade, FALLBACK)
        return {
            "jogo": alerta.jogo.nome if alerta.jogo else "",
            "slug": alerta.jogo.slug if alerta.jogo else "",
            "severidade": rotulo,
            "nivel": nivel,
            "icone": icone,
            "texto": alerta.texto,
        }

    def recentes(self, limite: int = 4) -> list:
        return self.repositorio.listar(
            pagina=1, por_pagina=limite, ordenar_por="-criado_em"
        ).itens
