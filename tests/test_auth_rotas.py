import requests
import responses

from app.auth.routes import _destino_seguro

USUARIO = {"id": 7, "nome_usuario": "Nikola98", "nivel": 12, "avatar_url": None}


def test_entrar_responde_200_no_get(client):
    assert client.get("/entrar").status_code == 200


def test_cadastrar_responde_200_no_get(client):
    assert client.get("/cadastrar").status_code == 200


@responses.activate
def test_login_valido_abre_a_sessao_e_vai_para_o_inicio(client):
    responses.post("http://api.test/api/login", json=USUARIO, status=200)

    resposta = client.post(
        "/entrar", data={"email": "nikola@exemplo.com", "senha": "segredo"}
    )

    assert resposta.status_code == 302
    assert resposta.headers["Location"] == "/"
    with client.session_transaction() as sessao:
        assert sessao["usuario"]["nome_usuario"] == "Nikola98"


@responses.activate
def test_credencial_errada_reexibe_o_formulario_com_recado(client):
    responses.post("http://api.test/api/login", json={"message": "nao"}, status=401)

    resposta = client.post(
        "/entrar", data={"email": "nikola@exemplo.com", "senha": "errada"}, follow_redirects=True
    )

    assert "E-mail ou senha incorretos." in resposta.get_data(as_text=True)
    with client.session_transaction() as sessao:
        assert "usuario" not in sessao


@responses.activate
def test_api_fora_do_ar_vira_recado_e_nao_erro_500(client):
    responses.post(
        "http://api.test/api/login", body=requests.exceptions.ConnectionError("recusado")
    )

    resposta = client.post(
        "/entrar", data={"email": "nikola@exemplo.com", "senha": "segredo"}
    )

    assert resposta.status_code == 200
    assert "servidor" in resposta.get_data(as_text=True)


def test_email_malformado_nao_passa_da_validacao(client):
    """O formulário barra antes da API — daí o recado ser de campo, não de servidor."""
    resposta = client.post("/entrar", data={"email": "nao-e-email", "senha": "x"})
    texto = resposta.get_data(as_text=True)

    assert resposta.status_code == 200
    assert "E-mail inválido." in texto
    assert "servidor" not in texto


@responses.activate
def test_cadastro_valido_ja_deixa_o_usuario_logado(client):
    responses.post("http://api.test/api/usuarios", json=USUARIO, status=201)

    resposta = client.post(
        "/cadastrar",
        data={
            "nome_usuario": "Nikola98",
            "email": "nikola@exemplo.com",
            "senha": "segredo123",
            "confirmacao": "segredo123",
        },
    )

    assert resposta.headers["Location"] == "/"
    with client.session_transaction() as sessao:
        assert sessao["usuario"]["id"] == 7


def test_senhas_diferentes_barram_o_cadastro(client):
    resposta = client.post(
        "/cadastrar",
        data={
            "nome_usuario": "Nikola98",
            "email": "nikola@exemplo.com",
            "senha": "segredo123",
            "confirmacao": "outra-coisa",
        },
    )

    assert "As senhas não conferem." in resposta.get_data(as_text=True)


@responses.activate
def test_erro_de_validacao_da_api_aparece_na_tela(client):
    responses.post(
        "http://api.test/api/usuarios",
        json={"message": "invalido", "errors": {"email": ["Já está em uso."]}},
        status=422,
    )

    resposta = client.post(
        "/cadastrar",
        data={
            "nome_usuario": "Nikola98",
            "email": "nikola@exemplo.com",
            "senha": "segredo123",
            "confirmacao": "segredo123",
        },
    )

    assert "Já está em uso." in resposta.get_data(as_text=True)


@responses.activate
def test_sair_limpa_a_sessao(client):
    responses.post("http://api.test/api/login", json=USUARIO, status=200)
    client.post("/entrar", data={"email": "nikola@exemplo.com", "senha": "segredo"})

    resposta = client.post("/sair")

    assert resposta.headers["Location"] == "/entrar"
    with client.session_transaction() as sessao:
        assert "usuario" not in sessao


def test_sair_recusa_get(client):
    assert client.get("/sair").status_code == 405


def test_destino_seguro_aceita_caminho_interno(app):
    with app.test_request_context():
        assert _destino_seguro("/biblioteca") == "/biblioteca"


def test_destino_seguro_recusa_site_externo(app):
    with app.test_request_context():
        assert _destino_seguro("https://malicioso.example/roubo") == "/"
        assert _destino_seguro("//malicioso.example") == "/"
        assert _destino_seguro(None) == "/"


def test_destino_seguro_recusa_barra_invertida(app):
    """`/\\host` passa num filtro ingênuo, mas o browser o lê como `//host`."""
    with app.test_request_context():
        assert _destino_seguro("/\\malicioso.example") == "/"
        assert _destino_seguro("/caminho\\malicioso.example") == "/"


def test_destino_seguro_recusa_caracteres_que_o_browser_remove(app):
    """Tab, LF e CR somem no parse: `/<TAB>/host` vira `//host` no browser."""
    with app.test_request_context():
        assert _destino_seguro("/\t/malicioso.example") == "/"
        assert _destino_seguro("/\n/malicioso.example") == "/"
        assert _destino_seguro("/\r/malicioso.example") == "/"


@responses.activate
def test_next_com_tab_nao_redireciona_para_fora(client):
    """Regressão ponta a ponta: esta era a via real do bypass."""
    responses.post("http://api.test/api/login", json=USUARIO, status=200)

    resposta = client.post(
        "/entrar?next=%2F%09%2Fmalicioso.example",
        data={"email": "nikola@exemplo.com", "senha": "segredo"},
    )

    assert resposta.headers["Location"] == "/"
