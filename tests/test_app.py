def test_saude_responde_ok(cliente):
    resposta = cliente.get("/saude")
    assert resposta.status_code == 200
    assert resposta.get_json() == {"status": "ok"}


def test_rota_inexistente_responde_json_e_nao_html(cliente):
    resposta = cliente.get("/nao-existe")
    assert resposta.status_code == 404
    assert resposta.content_type.startswith("application/json")
    assert resposta.get_json() == {"erro": "Recurso não encontrado."}


def test_json_preserva_acentuacao(app, cliente):
    from app.errors import NaoEncontrado

    @app.get("/erro-de-teste")
    def _erro():
        raise NaoEncontrado("Jogo não encontrado.")

    resposta = cliente.get("/erro-de-teste")
    assert resposta.status_code == 404
    assert "não" in resposta.get_data(as_text=True)
