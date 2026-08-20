"""Única camada Python que fala com a API Laravel (spec §4.3).

Existe porque a senha não pode transitar pelo JS. Todo o resto dos dados é
buscado pelo browser direto da API — se você estiver pensando em acrescentar
uma função de domínio aqui, ela está no lugar errado.
"""

from __future__ import annotations

import requests
from flask import current_app


class CredenciaisInvalidas(Exception):
    """A API recusou o par e-mail/senha."""


class DadosInvalidos(Exception):
    """A API recusou os dados enviados (HTTP 422)."""

    def __init__(self, erros: dict[str, list[str]]) -> None:
        super().__init__("Dados inválidos.")
        self.erros = erros


class ApiIndisponivel(Exception):
    """A API não respondeu, ou respondeu com erro de servidor."""


def _url(recurso: str) -> str:
    base = current_app.config["API_BASE_URL"].rstrip("/")
    return f"{base}/api/{recurso}"


def _postar(recurso: str, corpo: dict) -> requests.Response:
    try:
        return requests.post(
            _url(recurso), json=corpo, timeout=current_app.config["API_TIMEOUT"]
        )
    except requests.RequestException as erro:
        raise ApiIndisponivel(f"Sem resposta de {_url(recurso)}: {erro}") from erro


def autenticar(email: str, senha: str) -> dict:
    """Devolve o usuário da API, ou levanta CredenciaisInvalidas/ApiIndisponivel."""
    resposta = _postar("login", {"email": email, "senha": senha})

    if resposta.status_code == 200:
        return resposta.json()
    if resposta.status_code in (401, 422):
        raise CredenciaisInvalidas()
    raise ApiIndisponivel(f"HTTP {resposta.status_code} em {_url('login')}")


def registrar(nome_usuario: str, email: str, senha: str) -> dict:
    """Cria o usuário na API e devolve o objeto criado."""
    resposta = _postar(
        "usuarios", {"nome_usuario": nome_usuario, "email": email, "senha": senha}
    )

    if resposta.status_code == 201:
        return resposta.json()
    if resposta.status_code == 422:
        raise DadosInvalidos(resposta.json().get("errors", {}))
    raise ApiIndisponivel(f"HTTP {resposta.status_code} em {_url('usuarios')}")
