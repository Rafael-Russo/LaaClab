"""Proteções de request que o Django dava embutidas."""

from flask import Flask, abort, request


def register_host_check(app: Flask) -> None:
    """Rejeita requisições cujo cabeçalho ``Host`` não está na allowlist.

    Equivale ao ``ALLOWED_HOSTS`` do Django. Uma lista vazia desliga a
    checagem (usado em testes e em dev atrás de localhost).
    """

    @app.before_request
    def _checar_host():
        permitidos = app.config.get("ALLOWED_HOSTS") or []
        if not permitidos:
            return None
        host = request.host.split(":")[0]
        if host not in permitidos:
            abort(400, description="Host não permitido.")
        return None
