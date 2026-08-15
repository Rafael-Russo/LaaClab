from app.accounts.models import User
from app.extensions import db


def criar_e_logar(client, username="gamer"):
    usuario = User(username=username, email=f"{username}@example.com")
    usuario.set_password("segredo123")
    db.session.add(usuario)
    db.session.commit()
    with client.session_transaction() as sessao:
        sessao["_user_id"] = str(usuario.id)
        sessao["_fresh"] = True
    return usuario


def test_get_me_exige_autenticacao(client):
    assert client.get("/api/v1/me/").status_code == 401


def test_get_me_devolve_o_perfil(client):
    criar_e_logar(client)
    resposta = client.get("/api/v1/me/")
    assert resposta.status_code == 200
    corpo = resposta.get_json()
    assert corpo["username"] == "gamer"
    assert corpo["email"] == "gamer@example.com"
    assert corpo["level"] == 1
    assert corpo["theme"] == "dark"


def test_patch_altera_campos_editaveis(client):
    criar_e_logar(client)
    resposta = client.patch("/api/v1/me/", json={"handle": "novo", "bio": "olá"})
    assert resposta.status_code == 200
    corpo = resposta.get_json()
    assert corpo["handle"] == "novo"
    assert corpo["bio"] == "olá"


def test_patch_ignora_campos_somente_leitura(client):
    usuario = criar_e_logar(client)
    resposta = client.patch(
        "/api/v1/me/", json={"level": 99, "xp": 5000, "username": "outro"}
    )
    assert resposta.status_code == 200
    db.session.refresh(usuario.profile)
    assert usuario.profile.level == 1
    assert usuario.profile.xp == 0
    assert usuario.username == "gamer"


def test_patch_com_objeto_inteiro_do_get_aplica_so_o_editavel(client):
    """Cliente típico: GET, altera um campo, PATCH do objeto inteiro de volta.

    Campos somente-leitura devolvidos pelo GET (`level`, `xp`, `username`...)
    não podem fazer o PATCH inteiro ser rejeitado — têm que ser ignorados,
    como no `read_only_fields` do DRF.
    """
    criar_e_logar(client)
    corpo = client.get("/api/v1/me/").get_json()
    corpo["handle"] = "atualizado"
    resposta = client.patch("/api/v1/me/", json=corpo)
    assert resposta.status_code == 200
    assert resposta.get_json()["handle"] == "atualizado"
    assert resposta.get_json()["level"] == 1


def test_patch_so_altera_o_proprio_perfil(client):
    outro = User(username="outro", email="outro@example.com")
    outro.set_password("segredo123")
    db.session.add(outro)
    db.session.commit()
    criar_e_logar(client)
    client.patch("/api/v1/me/", json={"handle": "meu"})
    db.session.refresh(outro.profile)
    assert outro.profile.handle == "outro"


def test_patch_recusa_theme_invalido(client):
    criar_e_logar(client)
    assert client.patch("/api/v1/me/", json={"theme": "roxo"}).status_code == 422


def test_push_kinds_precisa_ser_lista_de_strings(client):
    criar_e_logar(client)
    assert client.patch("/api/v1/me/", json={"push_kinds": "reply"}).status_code == 422
    assert client.patch("/api/v1/me/", json={"push_kinds": ["reply"]}).status_code == 200


def test_o_recurso_aparece_no_openapi(client):
    caminhos = client.get("/api/v1/openapi.json").get_json()["paths"]
    assert "/api/v1/me/" in caminhos
