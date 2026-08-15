"""Proteções de request que o Django dava embutidas."""

import re

from flask import Flask, abort, redirect, request
from werkzeug.middleware.proxy_fix import ProxyFix

# ``hostname`` ou ``hostname:porta``; a porta é obrigatoriamente numérica e o
# literal IPv6 vem entre colchetes. Fatiar no primeiro ``:`` não serve: com
# ``Host: laaclab.example:evil.example`` o pedaço antes do ``:`` passaria pela
# allowlist enquanto ``request.host`` — usado depois para montar URLs absolutas,
# que é justamente o alvo do Host header injection — guardaria o valor
# envenenado inteiro. Host malformado é rejeitado, não remendado.
# ``\Z`` (não ``$``) no fim: ``$`` casa antes de um ``\n`` final, então
# ``"laaclab.example:8000\n"`` resolveria para ``"laaclab.example"`` em vez de
# ser rejeitado.
_HOST_RE = re.compile(r"^(?P<host>\[[0-9A-Fa-f:]+\]|[^:\[\]]+)(?::(?P<port>\d+))?\Z")


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


def register_proxy_fix(app: Flask) -> None:
    """Faz o Flask enxergar o esquema/host reais quando há proxy na frente.

    O nginx de ``deploy/nginx.conf`` já envia ``X-Forwarded-Proto``. Sem
    consumi-lo, ``request.is_secure`` é sempre falso: o ``WTF_CSRF_SSL_STRICT``
    nunca dispara e ``url_for(_external=True)`` gera links ``http://`` — nos
    e-mails de verificação e reset, entre outros. Fica sob flag porque confiar
    nesses cabeçalhos sem um proxy na frente é deixar o cliente forjá-los.

    ``x_host=0``: ``deploy/nginx.conf`` nunca define nem limpa
    ``X-Forwarded-Host``, então confiar nele deixaria o cliente influenciar
    ``request.host``. O Django que está sendo migrado nunca ligou
    ``USE_X_FORWARDED_HOST`` — essa não é uma confiança que a app de origem
    tinha.
    """
    if not app.config.get("TRUSTED_PROXY"):
        return
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=0)


def register_https_enforcement(app: Flask) -> None:
    """Redirect para HTTPS e header HSTS — o que o Django fazia com
    ``SECURE_SSL_REDIRECT`` e ``SECURE_HSTS_SECONDS``."""
    if app.config.get("SSL_REDIRECT"):

        @app.before_request
        def _forcar_https():
            if not request.is_secure:
                return redirect(request.url.replace("http://", "https://", 1), code=301)
            return None

    segundos = app.config.get("HSTS_SECONDS") or 0
    if segundos:

        @app.after_request
        def _hsts(resposta):
            if request.is_secure:
                resposta.headers.setdefault(
                    "Strict-Transport-Security",
                    f"max-age={segundos}; includeSubDomains; preload",
                )
            return resposta
