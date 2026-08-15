from sqlalchemy import delete

from app.accounts.models import Theme, User, UserProfile
from app.extensions import db


def criar_usuario(username="gamer", email="gamer@example.com", senha="segredo123"):
    usuario = User(username=username, email=email)
    usuario.set_password(senha)
    db.session.add(usuario)
    db.session.commit()
    return usuario


def test_perfil_nasce_com_o_usuario(app):
    usuario = criar_usuario()
    assert usuario.profile is not None
    assert usuario.profile.handle == "gamer"


def test_defaults_do_perfil(app):
    perfil = criar_usuario().profile
    assert perfil.level == 1
    assert perfil.xp == 0
    assert perfil.xp_max == 2000
    assert perfil.bio == ""
    assert perfil.avatar_color == "#6b7cff"
    assert perfil.achievements == 0
    assert perfil.friends == 0
    assert perfil.days_active == 0
    assert perfil.theme == Theme.DARK
    assert perfil.push_kinds == []


def test_perfil_e_um_por_usuario(app):
    a = criar_usuario("a", "a@example.com")
    b = criar_usuario("b", "b@example.com")
    assert a.profile.id != b.profile.id
    assert db.session.query(UserProfile).count() == 2


def test_apagar_usuario_apaga_o_perfil(app):
    usuario = criar_usuario()
    db.session.delete(usuario)
    db.session.commit()
    assert db.session.query(UserProfile).count() == 0


def test_theme_aceita_os_dois_valores(app):
    perfil = criar_usuario().profile
    perfil.theme = Theme.LIGHT
    db.session.commit()
    assert perfil.theme == "light"


def test_cascade_do_banco_apaga_o_perfil(app):
    """Prova o `ondelete=CASCADE` da migration, não o cascade do ORM.

    O delete vai por Core justamente para o `cascade="all, delete-orphan"` do
    relacionamento não poder ser o responsável — sem o PRAGMA do SQLite, este
    teste falha e o anterior continua passando.
    """
    usuario = criar_usuario()
    db.session.execute(delete(User.__table__).where(User.__table__.c.id == usuario.id))
    db.session.commit()
    assert db.session.query(UserProfile).count() == 0
