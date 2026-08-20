"""Proteção CSRF dos formulários (spec §4.2 e §9).

O `TestConfig` desliga o CSRF para que os demais testes não precisem carregar
token, e isso tem um preço: nada notaria se `csrf.init_app(app)` sumisse do
factory — nem o POST de `/sair`, a única mudança de estado do lado Flask.
Estes testes sobem um app com a proteção ligada, sem mexer no `TestConfig`.
"""

import re

import pytest
import responses

from app import create_app
from app.config import TestConfig

USUARIO = {"id": 7, "nome_usuario": "Nikola98", "nivel": 12, "avatar_url": None}
TOKEN_NO_HTML = re.compile(r'name="csrf_token"[^>]*value="([^"]+)"')


class ConfigComCsrf(TestConfig):
    """Igual ao `TestConfig`, menos pela proteção que ele desliga."""

    WTF_CSRF_ENABLED = True


@pytest.fixture
def cliente_com_csrf():
    return create_app(ConfigComCsrf).test_client()


@pytest.mark.parametrize("rota", ["/entrar", "/cadastrar", "/sair"])
def test_post_sem_token_csrf_e_recusado(cliente_com_csrf, rota):
    resposta = cliente_com_csrf.post(
        rota, data={"email": "nikola@exemplo.com", "senha": "segredo"}
    )

    assert resposta.status_code == 400


@responses.activate
def test_post_com_token_csrf_valido_segue_normalmente(cliente_com_csrf):
    """Contraprova: o 400 acima vem do CSRF, e não de outra coisa no caminho."""
    responses.post("http://api.test/api/login", json=USUARIO, status=200)
    formulario = cliente_com_csrf.get("/entrar").get_data(as_text=True)
    token = TOKEN_NO_HTML.search(formulario).group(1)

    resposta = cliente_com_csrf.post(
        "/entrar",
        data={"email": "nikola@exemplo.com", "senha": "segredo", "csrf_token": token},
    )

    assert resposta.status_code == 302
