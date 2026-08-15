"""O `HTTPException` handler é único e vale para a app inteira (ver
`app._register_error_handlers`): uma página que erra tem que continuar
devolvendo HTML/texto, e um recurso da API v1 tem que continuar devolvendo o
JSON do flask-smorest — mesmo depois do handler do smorest ter sido
substituído pelo nosso."""

from flask import abort


def test_pagina_desconhecida_nao_e_json(client):
    resposta = client.get("/rota-que-nao-existe")
    assert resposta.status_code == 404
    assert resposta.content_type != "application/json"


def test_recurso_de_api_desconhecido_e_json(client):
    resposta = client.get("/api/v1/rota-que-nao-existe")
    assert resposta.status_code == 404
    assert resposta.content_type == "application/json"
    assert resposta.get_json()["code"] == 404


def test_description_do_abort_chega_ao_cliente_em_pagina(app, client):
    """`module_required` chama `abort(404, description=...)`; o handler do
    smorest descartava essa `description` em silêncio. Fora da API ela
    precisa aparecer na resposta."""

    @app.get("/t/pagina-com-descricao")
    def _pagina():
        abort(404, description="módulo desativado")

    resposta = client.get("/t/pagina-com-descricao")
    assert resposta.status_code == 404
    assert resposta.content_type != "application/json"
    assert "módulo desativado".encode() in resposta.data


def test_erro_de_api_v1_preserva_o_formato_do_smorest(client):
    """Um 404 de rota inexistente sob `/api/v1/` mantém a forma
    `{"code": ..., "status": ...}` que o smorest sempre devolveu."""
    resposta = client.get("/api/v1/nao-existe/")
    corpo = resposta.get_json()
    assert set(corpo) >= {"code", "status"}
    assert corpo["status"] == "Not Found"
