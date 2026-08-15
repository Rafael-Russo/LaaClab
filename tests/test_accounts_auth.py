from app.accounts.models import User
from app.extensions import db


def criar_usuario(username="gamer", email="gamer@example.com", senha="segredo123"):
    usuario = User(username=username, email=email)
    usuario.set_password(senha)
    db.session.add(usuario)
    db.session.commit()
    return usuario


def test_get_login_renderiza(client):
    resposta = client.get("/accounts/login/")
    assert resposta.status_code == 200
    assert b"LaaC" in resposta.data


def test_login_com_credenciais_boas_autentica(client):
    criar_usuario()
    resposta = client.post(
        "/accounts/login/",
        data={"username": "gamer", "password": "segredo123"},
        follow_redirects=False,
    )
    assert resposta.status_code == 302
    with client.session_transaction() as sessao:
        assert "_user_id" in sessao


def test_login_com_senha_errada_nao_autentica(client):
    criar_usuario()
    resposta = client.post(
        "/accounts/login/", data={"username": "gamer", "password": "errada"}
    )
    assert resposta.status_code == 200  # re-renderiza o formulário
    with client.session_transaction() as sessao:
        assert "_user_id" not in sessao


def test_login_aceita_email_no_lugar_do_username(client):
    criar_usuario()
    client.post(
        "/accounts/login/",
        data={"username": "gamer@example.com", "password": "segredo123"},
    )
    with client.session_transaction() as sessao:
        assert "_user_id" in sessao


def test_login_de_usuario_inativo_e_recusado(client):
    usuario = criar_usuario()
    usuario.is_active = False
    db.session.commit()
    client.post("/accounts/login/", data={"username": "gamer", "password": "segredo123"})
    with client.session_transaction() as sessao:
        assert "_user_id" not in sessao


def test_get_signup_renderiza(client):
    assert client.get("/accounts/signup/").status_code == 200


def test_signup_cria_usuario_e_ja_autentica(client):
    resposta = client.post(
        "/accounts/signup/",
        data={
            "username": "novo",
            "email": "novo@example.com",
            "password1": "segredo123",
            "password2": "segredo123",
        },
    )
    assert resposta.status_code == 302
    usuario = db.session.query(User).filter_by(username="novo").one()
    assert usuario.check_password("segredo123")
    assert usuario.profile is not None
    with client.session_transaction() as sessao:
        assert sessao["_user_id"] == str(usuario.id)


def test_signup_recusa_senhas_diferentes(client):
    resposta = client.post(
        "/accounts/signup/",
        data={
            "username": "novo",
            "email": "novo@example.com",
            "password1": "segredo123",
            "password2": "outra12345",
        },
    )
    assert resposta.status_code == 200
    assert db.session.query(User).count() == 0


def test_signup_recusa_username_duplicado(client):
    criar_usuario(username="gamer")
    client.post(
        "/accounts/signup/",
        data={
            "username": "gamer",
            "email": "outro@example.com",
            "password1": "segredo123",
            "password2": "segredo123",
        },
    )
    assert db.session.query(User).count() == 1


def test_signup_recusa_email_duplicado(client):
    criar_usuario(email="mesmo@example.com")
    client.post(
        "/accounts/signup/",
        data={
            "username": "outro",
            "email": "mesmo@example.com",
            "password1": "segredo123",
            "password2": "segredo123",
        },
    )
    assert db.session.query(User).count() == 1


def test_logout_encerra_a_sessao(client):
    criar_usuario()
    client.post("/accounts/login/", data={"username": "gamer", "password": "segredo123"})
    resposta = client.post("/accounts/logout/")
    assert resposta.status_code == 302
    with client.session_transaction() as sessao:
        assert "_user_id" not in sessao


def test_rota_protegida_redireciona_anonimo_para_o_login(app, client):
    from flask_login import login_required

    @app.get("/t/protegida")
    @login_required
    def _protegida():
        return "ok"

    resposta = client.get("/t/protegida")
    assert resposta.status_code == 302
    assert "/accounts/login/" in resposta.headers["Location"]


def test_login_com_next_barra_invertida_nao_faz_open_redirect(client):
    """`/\\evil.example` começa com `/`, mas o WHATWG trata `\\` como `/`
    para http(s) — o browser resolveria isso como `https://evil.example`."""
    criar_usuario()
    resposta = client.post(
        "/accounts/login/?next=/\\evil.example",
        data={"username": "gamer", "password": "segredo123"},
    )
    assert resposta.status_code == 302
    assert "evil.example" not in resposta.headers["Location"]
    assert resposta.headers["Location"] == "/"


def test_login_com_next_duas_barras_nao_faz_open_redirect(client):
    criar_usuario()
    resposta = client.post(
        "/accounts/login/?next=//evil.example",
        data={"username": "gamer", "password": "segredo123"},
    )
    assert resposta.status_code == 302
    assert "evil.example" not in resposta.headers["Location"]
    assert resposta.headers["Location"] == "/"


def test_login_com_next_absoluto_nao_faz_open_redirect(client):
    criar_usuario()
    resposta = client.post(
        "/accounts/login/?next=https://evil.example",
        data={"username": "gamer", "password": "segredo123"},
    )
    assert resposta.status_code == 302
    assert "evil.example" not in resposta.headers["Location"]
    assert resposta.headers["Location"] == "/"


def test_login_com_next_relativo_e_honrado(client):
    criar_usuario()
    resposta = client.post(
        "/accounts/login/?next=/biblioteca/",
        data={"username": "gamer", "password": "segredo123"},
    )
    assert resposta.status_code == 302
    assert resposta.headers["Location"] == "/biblioteca/"


def test_next_fluxo_real_do_form_ate_o_redirect(client):
    """O browser nunca manda `?next=` de volta no POST: a página de login é
    servida em `/accounts/login/?next=...`, mas o form posta sem query string
    e carrega o `next` num campo oculto. Este teste percorre exatamente esse
    caminho, em vez de simular o POST direto na URL com `?next=`."""
    criar_usuario()

    pagina = client.get("/accounts/login/?next=/biblioteca/")
    assert resposta_contem_campo_next(pagina.data, "/biblioteca/")

    resposta = client.post(
        "/accounts/login/",
        data={"username": "gamer", "password": "segredo123", "next": "/biblioteca/"},
    )
    assert resposta.status_code == 302
    assert resposta.headers["Location"] == "/biblioteca/"


def resposta_contem_campo_next(html: bytes, valor: str) -> bool:
    corpo = html.decode()
    return (
        '<input type="hidden" name="next"' in corpo
        and f'value="{valor}"' in corpo
    )


def test_login_compara_hash_mesmo_sem_usuario(client, monkeypatch):
    """Proxy observável da equalização de tempo: o hash descartável precisa
    ser comparado mesmo quando não existe usuário com esse identificador,
    senão o tempo de resposta entrega que a conta não existe."""
    from app.accounts import views

    chamadas = []
    original = views.check_password_hash

    def _rastreado(hash_, senha):
        chamadas.append((hash_, senha))
        return original(hash_, senha)

    monkeypatch.setattr(views, "check_password_hash", _rastreado)
    client.post(
        "/accounts/login/",
        data={"username": "fantasma", "password": "qualquer123"},
    )
    assert chamadas, "check_password_hash deveria rodar mesmo sem usuário"


def test_sessao_de_usuario_desativado_vira_anonima(app, client):
    """`_load_user` só devolve o usuário se `is_active` — sem isso a sessão de
    uma conta desativada continua autenticada até expirar sozinha, ao
    contrário do `ModelBackend.get_user()` do Django, que já devolve `None`."""
    from flask_login import login_required

    @app.get("/t/protegida-desativacao")
    @login_required
    def _protegida():
        return "ok"

    usuario = criar_usuario()
    client.post(
        "/accounts/login/", data={"username": "gamer", "password": "segredo123"}
    )
    with client.session_transaction() as sessao:
        assert "_user_id" in sessao

    usuario.is_active = False
    db.session.commit()

    pagina = client.get("/t/protegida-desativacao")
    assert pagina.status_code == 302
    assert "/accounts/login/" in pagina.headers["Location"]

    api = client.get("/api/v1/me/")
    assert api.status_code == 401


def test_login_com_email_maiusculo_do_signup_funciona(client):
    """Signup guarda o e-mail em minúsculas; login por e-mail comparava sem
    normalizar, então quem digitasse maiúsculas no signup (autofill costuma
    repetir o que foi digitado) nunca mais conseguiria entrar."""
    client.post(
        "/accounts/signup/",
        data={
            "username": "novo",
            "email": "Gamer@Example.com",
            "password1": "segredo123",
            "password2": "segredo123",
        },
    )
    client.post("/accounts/logout/")
    with client.session_transaction() as sessao:
        assert "_user_id" not in sessao

    client.post(
        "/accounts/login/",
        data={"username": "Gamer@Example.com", "password": "segredo123"},
    )
    with client.session_transaction() as sessao:
        assert "_user_id" in sessao
