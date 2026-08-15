import pytest
from flask import jsonify

from app.accounts.models import Role, User
from app.core.decorators import (
    api_login_required,
    module_required,
    module_required_api,
    perm_required,
    staff_required,
)
from app.core.models import Module
from app.extensions import db


@pytest.fixture
def rotas(app):
    """Monta rotas de teste em cima da app da fixture, uma por decorator."""

    @app.get("/t/api-login")
    @api_login_required
    def _api_login():
        return jsonify({"ok": True})

    @app.get("/t/staff")
    @staff_required
    def _staff():
        return jsonify({"ok": True})

    @app.get("/t/perm")
    @perm_required("community.can_moderate_forum")
    def _perm():
        return jsonify({"ok": True})

    @app.get("/t/pagina")
    @module_required("community")
    def _pagina():
        return "ok"

    @app.get("/t/api-modulo")
    @module_required_api("community")
    def _api_modulo():
        return jsonify({"ok": True})

    return app.test_client()


def criar_usuario(username="gamer", is_staff=False, permissoes=None):
    usuario = User(username=username, email=f"{username}@example.com", is_staff=is_staff)
    usuario.set_password("segredo123")
    if permissoes:
        usuario.roles.append(Role(name=f"r-{username}", label="", permissions=permissoes))
    db.session.add(usuario)
    db.session.commit()
    return usuario


def logar(client, usuario):
    with client.session_transaction() as sessao:
        sessao["_user_id"] = str(usuario.id)
        sessao["_fresh"] = True


def test_api_login_required_devolve_401_json_para_anonimo(rotas):
    resposta = rotas.get("/t/api-login")
    assert resposta.status_code == 401
    assert resposta.get_json() == {"detail": "Autenticação necessária."}


def test_api_login_required_passa_autenticado(rotas):
    logar(rotas, criar_usuario())
    assert rotas.get("/t/api-login").status_code == 200


def test_staff_required_bloqueia_usuario_comum(rotas):
    logar(rotas, criar_usuario())
    assert rotas.get("/t/staff").status_code == 403


def test_staff_required_passa_staff(rotas):
    logar(rotas, criar_usuario(is_staff=True))
    assert rotas.get("/t/staff").status_code == 200


def test_staff_required_bloqueia_anonimo(rotas):
    assert rotas.get("/t/staff").status_code in (401, 403)


def test_perm_required_bloqueia_sem_a_permissao(rotas):
    logar(rotas, criar_usuario())
    assert rotas.get("/t/perm").status_code == 403


def test_perm_required_passa_com_a_permissao(rotas):
    logar(rotas, criar_usuario(permissoes=["community.can_moderate_forum"]))
    assert rotas.get("/t/perm").status_code == 200


def test_perm_required_passa_staff(rotas):
    logar(rotas, criar_usuario(is_staff=True))
    assert rotas.get("/t/perm").status_code == 200


def test_module_required_404_quando_desligado(rotas):
    db.session.add(Module(key="community", name="Comunidade", enabled=False))
    db.session.commit()
    assert rotas.get("/t/pagina").status_code == 404


def test_module_required_passa_quando_ligado(rotas):
    assert rotas.get("/t/pagina").status_code == 200


def test_module_required_api_404_json_quando_desligado(rotas):
    db.session.add(Module(key="community", name="Comunidade", enabled=False))
    db.session.commit()
    resposta = rotas.get("/t/api-modulo")
    assert resposta.status_code == 404
    assert resposta.get_json() == {"detail": "módulo desativado"}
