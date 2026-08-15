from app.accounts.models import Role, User
from app.core.models import Module
from app.extensions import db

ROLES_ESPERADAS = {
    "Administrador",
    "Moderador de Fórum",
    "Moderador de Jogos/Bugs",
    "Usuário",
}


def test_setup_permissions_cria_as_roles(app):
    resultado = app.test_cli_runner().invoke(args=["setup-permissions"])
    assert resultado.exit_code == 0
    assert {r.name for r in db.session.query(Role).all()} == ROLES_ESPERADAS


def test_setup_permissions_atribui_as_permissoes(app):
    app.test_cli_runner().invoke(args=["setup-permissions"])
    por_nome = {r.name: r for r in db.session.query(Role).all()}
    assert "community.can_moderate_forum" in por_nome["Moderador de Fórum"].permissions
    assert "catalog.can_moderate_games" in por_nome["Moderador de Jogos/Bugs"].permissions
    assert set(por_nome["Administrador"].permissions) == {
        "community.can_moderate_forum",
        "catalog.can_moderate_games",
    }
    assert por_nome["Usuário"].permissions == []


def test_setup_permissions_e_idempotente(app):
    runner = app.test_cli_runner()
    runner.invoke(args=["setup-permissions"])
    runner.invoke(args=["setup-permissions"])
    assert db.session.query(Role).count() == 4


def test_modules_list_sem_nada_registrado(app):
    resultado = app.test_cli_runner().invoke(args=["modules", "--list"])
    assert resultado.exit_code == 0
    assert "Nenhum módulo registrado" in resultado.output


def test_modules_enable_cria_e_liga(app):
    resultado = app.test_cli_runner().invoke(args=["modules", "--enable", "community"])
    assert resultado.exit_code == 0
    assert db.session.query(Module).filter_by(key="community").one().enabled is True


def test_modules_disable_desliga(app):
    runner = app.test_cli_runner()
    runner.invoke(args=["modules", "--enable", "alerts"])
    runner.invoke(args=["modules", "--disable", "alerts"])
    assert db.session.query(Module).filter_by(key="alerts").one().enabled is False


def test_modules_list_mostra_o_estado(app):
    runner = app.test_cli_runner()
    runner.invoke(args=["modules", "--disable", "alerts"])
    saida = runner.invoke(args=["modules", "--list"]).output
    assert "alerts" in saida
    assert "off" in saida


def test_seed_cria_o_usuario_de_demonstracao(app):
    resultado = app.test_cli_runner().invoke(args=["seed"])
    assert resultado.exit_code == 0
    gamer = db.session.query(User).filter_by(username="gamer").one()
    assert gamer.check_password("gamerpass123")
    assert gamer.profile is not None


def test_seed_registra_os_modulos(app):
    app.test_cli_runner().invoke(args=["seed"])
    chaves = {m.key for m in db.session.query(Module).all()}
    assert chaves == {"catalog", "community", "alerts"}


def test_seed_e_idempotente(app):
    runner = app.test_cli_runner()
    runner.invoke(args=["seed"])
    runner.invoke(args=["seed"])
    assert db.session.query(User).filter_by(username="gamer").count() == 1
    assert db.session.query(Module).count() == 3
    assert db.session.query(Role).count() == 4
