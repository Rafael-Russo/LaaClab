"""Formatação de apresentação que fica no servidor.

Vocabulário em português é domínio, não estilo — por isso o tempo relativo
mora aqui e não no JS. Formatação numérica de locale, essa sim, é do JS.
"""
from datetime import datetime, timezone

_ESCALAS = [
    (365 * 24 * 3600, "ano", "anos"),
    (30 * 24 * 3600, "mês", "meses"),
    (24 * 3600, "dia", "dias"),
    (3600, "hora", "horas"),
    (60, "minuto", "minutos"),
]


def tempo_relativo(quando: datetime, agora_utc: datetime | None = None) -> str:
    """'há 3 minutos'. Só a maior unidade, como o Django fazia ao cortar
    na primeira vírgula."""
    if quando is None:
        return ""

    agora = agora_utc or datetime.now(timezone.utc)
    # Colunas DateTime do SQLAlchemy voltam sem tzinfo.
    if quando.tzinfo is None:
        quando = quando.replace(tzinfo=timezone.utc)
    if agora.tzinfo is None:
        agora = agora.replace(tzinfo=timezone.utc)

    segundos = int((agora - quando).total_seconds())
    if segundos < 60:
        return "agora mesmo"

    for tamanho, singular, plural in _ESCALAS:
        if segundos >= tamanho:
            quantidade = segundos // tamanho
            unidade = singular if quantidade == 1 else plural
            return f"há {quantidade} {unidade}"
    return "agora mesmo"


def duracao_jogada(minutos: int | None) -> str:
    """'29h 27m'. Substitui a fórmula falsa `bug_score // 3` do sistema
    antigo, que exibia pontuação de bug como se fosse tempo de jogo."""
    total = max(0, int(minutos or 0))
    return f"{total // 60}h {total % 60:02d}m"
