import pytest

from app.errors import Conflito, DadosInvalidos, NaoAutorizado


# ----------------------------------------------------------------- service
def test_auth_service_nao_conhece_jwt():
    """Emitir token é responsabilidade do Controller.

    Olha os imports via `ast` e os nomes usados no código, não o texto —
    a docstring do módulo menciona JWT ao explicar que não o conhece.
    """
    import ast

    import app.services.auth_service as modulo

    arvore = ast.parse(open(modulo.__file__, encoding="utf-8").read())
    for no in ast.walk(arvore):
        if isinstance(no, ast.Import):
            for alias in no.names:
                assert not alias.name.startswith("flask"), alias.name
        if isinstance(no, ast.ImportFrom):
            assert not (no.module or "").startswith("flask"), no.module
        if isinstance(no, ast.Name):
            assert no.id != "create_access_token"


def test_registrar_cria_usuario_com_senha_hasheada(app):
    from app.composicao import montar_servicos

    servicos = montar_servicos()
    usuario, status = servicos.auth.registrar(
        {"nome_usuario": "gamer", "email": "g@l.dev", "senha": "senha123"}
    )
    assert status == 201
    assert usuario["nome_usuario"] == "gamer"
    assert "senha_hash" not in usuario


def test_registrar_aplica_apelido_padrao_igual_ao_nome(app):
    from app.composicao import montar_servicos

    servicos = montar_servicos()
    usuario, _ = servicos.auth.registrar(
        {"nome_usuario": "gamer", "email": "g@l.dev", "senha": "senha123"}
    )
    assert usuario["apelido"] == "gamer"


def test_registrar_nome_repetido_levanta_conflito(app):
    from app.composicao import montar_servicos

    servicos = montar_servicos()
    servicos.auth.registrar(
        {"nome_usuario": "gamer", "email": "a@l.dev", "senha": "senha123"}
    )
    with pytest.raises(Conflito) as excecao:
        servicos.auth.registrar(
            {"nome_usuario": "gamer", "email": "b@l.dev", "senha": "senha123"}
        )
    assert excecao.value.status == 409


def test_registrar_email_repetido_levanta_conflito(app):
    from app.composicao import montar_servicos

    servicos = montar_servicos()
    # Nomes com 3+ caracteres: o schema exige isso, e um nome curto
    # dispararia 422 antes de chegar na checagem de email duplicado.
    servicos.auth.registrar(
        {"nome_usuario": "primeiro", "email": "mesmo@l.dev", "senha": "senha123"}
    )
    with pytest.raises(Conflito):
        servicos.auth.registrar(
            {"nome_usuario": "segundo", "email": "mesmo@l.dev", "senha": "senha123"}
        )


def test_registrar_senha_curta_levanta_dados_invalidos(app):
    from app.composicao import montar_servicos

    servicos = montar_servicos()
    with pytest.raises(DadosInvalidos) as excecao:
        servicos.auth.registrar(
            {"nome_usuario": "gamer", "email": "g@l.dev", "senha": "curta"}
        )
    assert "senha" in excecao.value.erros


def test_autenticar_aceita_nome_de_usuario(app):
    from app.composicao import montar_servicos

    servicos = montar_servicos()
    servicos.auth.registrar(
        {"nome_usuario": "gamer", "email": "g@l.dev", "senha": "senha123"}
    )
    usuario, status = servicos.auth.autenticar(
        {"identificador": "gamer", "senha": "senha123"}
    )
    assert status == 200
    assert usuario["nome_usuario"] == "gamer"


def test_autenticar_aceita_email(app):
    from app.composicao import montar_servicos

    servicos = montar_servicos()
    servicos.auth.registrar(
        {"nome_usuario": "gamer", "email": "g@l.dev", "senha": "senha123"}
    )
    usuario, _ = servicos.auth.autenticar(
        {"identificador": "g@l.dev", "senha": "senha123"}
    )
    assert usuario["nome_usuario"] == "gamer"


def test_autenticar_senha_errada_levanta_401(app):
    from app.composicao import montar_servicos

    servicos = montar_servicos()
    servicos.auth.registrar(
        {"nome_usuario": "gamer", "email": "g@l.dev", "senha": "senha123"}
    )
    with pytest.raises(NaoAutorizado) as excecao:
        servicos.auth.autenticar({"identificador": "gamer", "senha": "errada"})
    assert excecao.value.status == 401


def test_autenticar_usuario_inexistente_levanta_401_e_nao_404(app):
    """Não revelar se o usuário existe."""
    from app.composicao import montar_servicos

    servicos = montar_servicos()
    with pytest.raises(NaoAutorizado) as excecao:
        servicos.auth.autenticar({"identificador": "ninguem", "senha": "senha123"})
    assert excecao.value.status == 401


# -------------------------------------------------------------- controller
def test_post_registro_devolve_201_com_tokens(cliente):
    resposta = cliente.post(
        "/api/auth/registro",
        json={"nome_usuario": "gamer", "email": "g@l.dev", "senha": "senha123"},
    )
    assert resposta.status_code == 201
    corpo = resposta.get_json()
    assert corpo["usuario"]["nome_usuario"] == "gamer"
    assert corpo["token_acesso"]
    assert corpo["token_renovacao"]


def test_post_login_devolve_tokens(cliente):
    cliente.post(
        "/api/auth/registro",
        json={"nome_usuario": "gamer", "email": "g@l.dev", "senha": "senha123"},
    )
    resposta = cliente.post(
        "/api/auth/login", json={"identificador": "gamer", "senha": "senha123"}
    )
    assert resposta.status_code == 200
    assert resposta.get_json()["token_acesso"]


def test_post_login_errado_devolve_401_em_json(cliente):
    resposta = cliente.post(
        "/api/auth/login", json={"identificador": "ninguem", "senha": "senha123"}
    )
    assert resposta.status_code == 401
    assert resposta.content_type.startswith("application/json")
    assert resposta.get_json() == {"erro": "Credenciais inválidas."}


def test_renovar_troca_token_de_renovacao_por_acesso(cliente):
    registro = cliente.post(
        "/api/auth/registro",
        json={"nome_usuario": "gamer", "email": "g@l.dev", "senha": "senha123"},
    ).get_json()

    resposta = cliente.post(
        "/api/auth/renovar",
        headers={"Authorization": f"Bearer {registro['token_renovacao']}"},
    )
    assert resposta.status_code == 200
    assert resposta.get_json()["token_acesso"]


def test_renovar_com_token_de_acesso_e_recusado(cliente):
    """Mandar o token errado na rota de renovação é recusado com 401.

    O `invalid_token_loader` registrado no factory normaliza TODO
    problema de token para 401 — expirado, malformado ou do tipo errado.
    É proposital: o front reage ao status, e só 401 dispara o redirect
    para o login.
    """
    registro = cliente.post(
        "/api/auth/registro",
        json={"nome_usuario": "gamer", "email": "g@l.dev", "senha": "senha123"},
    ).get_json()

    resposta = cliente.post(
        "/api/auth/renovar",
        headers={"Authorization": f"Bearer {registro['token_acesso']}"},
    )
    assert resposta.status_code == 401
    assert resposta.content_type.startswith("application/json")


def test_requisicao_sem_token_responde_401_nunca_403(cliente):
    """Se responder 403, o front não redireciona para o login."""
    resposta = cliente.post("/api/auth/renovar")
    assert resposta.status_code == 401
    assert resposta.get_json() == {"erro": "Autenticação necessária."}
