"""Apresentação do alerta: severidade → rótulo, nível e ícone."""
from app.services.base import ServicoBase

#: severidade → (rótulo exibido, nível CSS, ícone)
#: ATENÇÃO: 'atualizacao' vira nível 'stable', não 'update'. Não existe
#: classe .badge--update no CSS — emitir 'update' deixa o selo sem cor.
APRESENTACAO = {
    "critica": ("CRÍTICO", "critical", "wifi"),
    "instavel": ("INSTÁVEL", "warning", "alert"),
    "atualizacao": ("Atualização", "stable", "check"),
}

FALLBACK = ("CRÍTICO", "critical", "wifi")


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
