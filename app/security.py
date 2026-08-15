"""Proteções de request que o Django dava embutidas."""

import re

from flask import Flask, abort, request

# ``hostname`` ou ``hostname:porta``; a porta é obrigatoriamente numérica e o
# literal IPv6 vem entre colchetes. Fatiar no primeiro ``:`` não serve: com
# ``Host: laaclab.example:evil.example`` o pedaço antes do ``:`` passaria pela
# allowlist enquanto ``request.host`` — usado depois para montar URLs absolutas,
# que é justamente o alvo do Host header injection — guardaria o valor
# envenenado inteiro. Host malformado é rejeitado, não remendado.
_HOST_RE = re.compile(r"^(?P<host>\[[0-9A-Fa-f:]+\]|[^:\[\]]+)(?::(?P<port>\d+))?$")


def _hostname(raw: str) -> str | None:
    """Hostname em minúsculas, ou ``None`` se o ``Host`` for malformado."""
    match = _HOST_RE.match(raw)
    return match.group("host").lower() if match else None


def register_host_check(app: Flask) -> None:
    """Rejeita requisições cujo cabeçalho ``Host`` não está na allowlist.

    Equivale ao ``ALLOWED_HOSTS`` do Django. Uma lista vazia desliga a
    checagem (usado em testes e em dev atrás de localhost). A comparação é
    case-insensitive porque nomes de domínio são.
    """

    @app.before_request
    def _checar_host():
        permitidos = app.config.get("ALLOWED_HOSTS") or []
        if not permitidos:
            return None
        host = _hostname(request.host)
        if host is None or host not in {h.lower() for h in permitidos}:
            abort(400, description="Host não permitido.")
        return None
