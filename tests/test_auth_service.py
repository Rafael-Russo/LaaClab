import json

import pytest
import requests
import responses

from app.auth.service import (
    ApiIndisponivel,
    CredenciaisInvalidas,
    DadosInvalidos,
    autenticar,
    registrar,
)

USUARIO = {
    "id": 7,
    "nome_usuario": "Nikola98",
    "email": "nikola@exemplo.com",
    "nivel": 12,
    "avatar_url": None,
}


@responses.activate
def test_autenticar_devolve_o_usuario_quando_a_api_responde_200(app):
    responses.post("http://api.test/api/login", json=USUARIO, status=200)

    with app.app_context():
        assert autenticar("nikola@exemplo.com", "segredo") == USUARIO


@responses.activate
def test_autenticar_envia_email_e_senha_no_corpo(app):
    responses.post("http://api.test/api/login", json=USUARIO, status=200)

    with app.app_context():
        autenticar("nikola@exemplo.com", "segredo")

    assert json.loads(responses.calls[0].request.body) == {
        "email": "nikola@exemplo.com",
        "senha": "segredo",
    }


@responses.activate
def test_as_chamadas_pedem_json_explicitamente(app):
    """O Laravel decide entre 422 JSON e 302 HTML por `expectsJson()`.

    `Accept: */*` — o padrão do `requests` — não satisfaz `expectsJson()`, e o
    caminho de `DadosInvalidos` nunca dispararia contra uma API real.
    """
    responses.post("http://api.test/api/login", json=USUARIO, status=200)

    with app.app_context():
        autenticar("nikola@exemplo.com", "segredo")

    assert responses.calls[0].request.headers["Accept"] == "application/json"


@responses.activate
def test_autenticar_levanta_credenciais_invalidas_no_401(app):
    responses.post("http://api.test/api/login", json={"message": "nao"}, status=401)

    with app.app_context(), pytest.raises(CredenciaisInvalidas):
        autenticar("nikola@exemplo.com", "errada")


@responses.activate
def test_autenticar_levanta_api_indisponivel_no_500(app):
    responses.post("http://api.test/api/login", json={}, status=500)

    with app.app_context(), pytest.raises(ApiIndisponivel):
        autenticar("nikola@exemplo.com", "segredo")


@responses.activate
def test_autenticar_levanta_api_indisponivel_quando_nao_ha_resposta(app):
    responses.post(
        "http://api.test/api/login", body=requests.exceptions.ConnectionError("recusado")
    )

    with app.app_context(), pytest.raises(ApiIndisponivel):
        autenticar("nikola@exemplo.com", "segredo")


@responses.activate
def test_registrar_devolve_o_usuario_criado_no_201(app):
    responses.post("http://api.test/api/usuarios", json=USUARIO, status=201)

    with app.app_context():
        assert registrar("Nikola98", "nikola@exemplo.com", "segredo123")["id"] == 7


@responses.activate
def test_registrar_expoe_os_erros_de_validacao_no_422(app):
    responses.post(
        "http://api.test/api/usuarios",
        json={"message": "invalido", "errors": {"email": ["Já está em uso."]}},
        status=422,
    )

    with app.app_context(), pytest.raises(DadosInvalidos) as capturado:
        registrar("Nikola98", "nikola@exemplo.com", "segredo123")

    assert capturado.value.erros == {"email": ["Já está em uso."]}


@responses.activate
def test_a_url_e_montada_com_o_sufixo_api(app):
    responses.post("http://api.test/api/login", json=USUARIO, status=200)

    with app.app_context():
        autenticar("nikola@exemplo.com", "segredo")

    assert responses.calls[0].request.url == "http://api.test/api/login"
