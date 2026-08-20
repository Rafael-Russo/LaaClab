from flask_login import current_user, login_user

from app.auth.usuario import Usuario

DA_API = {
    "id": 7,
    "nome_usuario": "Nikola98",
    "email": "nikola@exemplo.com",
    "nivel": 12,
    "avatar_url": "https://exemplo.com/avatar.png",
    "bio": "Jogando e evoluindo.",
}


def test_da_api_pega_so_o_que_a_shell_precisa():
    usuario = Usuario.da_api(DA_API)

    assert (usuario.id, usuario.nome_usuario, usuario.nivel) == (7, "Nikola98", 12)
    assert usuario.avatar_url == "https://exemplo.com/avatar.png"
    assert not hasattr(usuario, "bio")


def test_nivel_ausente_cai_para_um():
    assert Usuario.da_api({"id": 1, "nome_usuario": "x"}).nivel == 1


def test_para_sessao_e_da_sessao_fazem_ida_e_volta():
    original = Usuario.da_api(DA_API)

    reconstruido = Usuario.da_sessao(original.para_sessao())

    assert reconstruido.para_sessao() == original.para_sessao()


def test_para_sessao_nao_carrega_email_nem_bio():
    """A sessão guarda o mínimo (spec §4.2), não o perfil inteiro."""
    dados = Usuario.da_api(DA_API).para_sessao()

    assert set(dados) == {"id", "nome_usuario", "avatar_url", "nivel"}


def test_get_id_devolve_string_como_o_flask_login_espera():
    assert Usuario.da_api(DA_API).get_id() == "7"


def test_o_user_loader_reconstroi_o_usuario_da_sessao(app):
    with app.test_request_context():
        login_user(Usuario.da_api(DA_API))

        assert current_user.is_authenticated
        assert current_user.nome_usuario == "Nikola98"


def test_sessao_vazia_nao_autentica_ninguem(app):
    with app.test_request_context():
        assert not current_user.is_authenticated
