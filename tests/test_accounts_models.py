import pytest
from sqlalchemy.exc import IntegrityError

from app.accounts.models import Role, User
from app.extensions import db


def criar_usuario(username="gamer", email="gamer@example.com", senha="segredo123", **kwargs):
    usuario = User(username=username, email=email, **kwargs)
    usuario.set_password(senha)
    db.session.add(usuario)
    db.session.commit()
    return usuario


def test_senha_e_guardada_como_hash(app):
    usuario = criar_usuario(senha="segredo123")
    assert usuario.password_hash != "segredo123"
    assert usuario.check_password("segredo123") is True
    assert usuario.check_password("errada") is False


def test_username_e_unico(app):
    criar_usuario(username="gamer", email="a@example.com")
    with pytest.raises(IntegrityError):
        criar_usuario(username="gamer", email="b@example.com")


def test_email_e_unico(app):
    criar_usuario(username="a", email="mesmo@example.com")
    with pytest.raises(IntegrityError):
        criar_usuario(username="b", email="mesmo@example.com")


def test_defaults_do_usuario(app):
    usuario = criar_usuario()
    assert usuario.is_active is True
    assert usuario.is_staff is False
    assert usuario.email_verified is False
    assert usuario.date_joined is not None


def test_has_perm_falso_sem_role(app):
    usuario = criar_usuario()
    assert usuario.has_perm("community.can_moderate_forum") is False


def test_has_perm_verdadeiro_pela_role(app):
    usuario = criar_usuario()
    role = Role(name="Moderador de Fórum", label="Modera o fórum",
                permissions=["community.can_moderate_forum"])
    usuario.roles.append(role)
    db.session.commit()
    assert usuario.has_perm("community.can_moderate_forum") is True
    assert usuario.has_perm("catalog.can_moderate_games") is False


def test_staff_tem_todas_as_permissoes(app):
    usuario = criar_usuario(is_staff=True)
    assert usuario.has_perm("catalog.can_moderate_games") is True
    assert usuario.has_perm("qualquer.coisa") is True


def test_staff_desativado_nao_tem_permissao_nenhuma(app):
    """`is_active` vem antes de staff em `has_perm`, como no `ModelBackend`
    do Django — sem isso uma conta staff desativada continuaria autorizada
    em qualquer chamada direta ao método."""
    usuario = criar_usuario(is_staff=True, is_active=False)
    assert usuario.has_perm("qualquer.coisa") is False


def test_usuario_pode_ter_varias_roles(app):
    usuario = criar_usuario()
    usuario.roles.append(Role(name="A", label="a", permissions=["x.um"]))
    usuario.roles.append(Role(name="B", label="b", permissions=["x.dois"]))
    db.session.commit()
    assert usuario.has_perm("x.um") is True
    assert usuario.has_perm("x.dois") is True


def test_user_loader_resolve_o_usuario(app):
    usuario = criar_usuario()
    assert app.login_manager._user_callback(str(usuario.id)) is usuario


def test_user_loader_devolve_none_para_id_invalido(app):
    assert app.login_manager._user_callback("999") is None
    assert app.login_manager._user_callback("nao-numero") is None
