"""Comandos de linha de comando.

Portam os `management/commands` do Django. Todos idempotentes: rodar duas
vezes deixa o mesmo estado, porque o `entrypoint.sh` os chama a cada boot.
"""

import click
from flask import Flask

from app.accounts.models import Role, User
from app.core.models import Module
from app.extensions import db

# Só as duas permissões que o código realmente consulta. As 15 permissões CRUD
# que o `setup_permissions` do Django criava serviam ao admin, que saiu de
# escopo na migração.
FORUM_MOD = "community.can_moderate_forum"
GAMES_MOD = "catalog.can_moderate_games"

ROLES = {
    "Administrador": ("Acesso total", [FORUM_MOD, GAMES_MOD]),
    "Moderador de Fórum": ("Modera tópicos, respostas e comentários", [FORUM_MOD]),
    "Moderador de Jogos/Bugs": ("Modera o catálogo e os bugs", [GAMES_MOD]),
    "Usuário": ("Usuário comum, sem moderação", []),
}

NOMES_DE_MODULO = {
    "catalog": "Catálogo",
    "community": "Comunidade",
    "alerts": "Alertas",
}


def register_cli(app: Flask) -> None:
    app.cli.add_command(setup_permissions)
    app.cli.add_command(modules)
    app.cli.add_command(seed)


@click.command("setup-permissions")
def setup_permissions():
    """Cria ou atualiza as roles padrão e suas permissões."""
    _aplicar_roles()
    click.echo("Roles configuradas.")


@click.command("modules")
@click.option("--list", "listar", is_flag=True, help="Lista os módulos conhecidos.")
@click.option("--enable", "ligar", metavar="KEY", help="Liga o módulo.")
@click.option("--disable", "desligar", metavar="KEY", help="Desliga o módulo.")
def modules(listar, ligar, desligar):
    """Lista, liga ou desliga módulos de funcionalidade."""
    if ligar:
        _definir_modulo(ligar, True)
    if desligar:
        _definir_modulo(desligar, False)
    if listar or not (ligar or desligar):
        _listar_modulos()


@click.command("seed")
def seed():
    """Popula identidade e módulos com dados de demonstração."""
    _aplicar_roles()
    for chave, nome in NOMES_DE_MODULO.items():
        if not db.session.query(Module).filter_by(key=chave).first():
            db.session.add(Module(key=chave, name=nome, enabled=True))
    db.session.commit()

    if not db.session.query(User).filter_by(username="gamer").first():
        gamer = User(username="gamer", email="gamer@laaclab.example")
        gamer.set_password("gamerpass123")
        db.session.add(gamer)
        db.session.commit()
        click.echo("Usuário de demonstração criado: gamer / gamerpass123")
    click.echo("Seed concluído.")


def _aplicar_roles() -> None:
    """Fetch-or-create e reaplica as permissões — daí a idempotência."""
    for nome, (rotulo, permissoes) in ROLES.items():
        role = db.session.query(Role).filter_by(name=nome).first()
        if role is None:
            role = Role(name=nome)
            db.session.add(role)
        role.label = rotulo
        role.permissions = list(permissoes)
    db.session.commit()


def _definir_modulo(chave: str, ligado: bool) -> None:
    modulo = db.session.query(Module).filter_by(key=chave).first()
    if modulo is None:
        modulo = Module(key=chave, name=NOMES_DE_MODULO.get(chave, chave))
        db.session.add(modulo)
    modulo.enabled = ligado
    db.session.commit()
    click.echo(f"{chave}: {'on' if ligado else 'off'}")


def _listar_modulos() -> None:
    todos = db.session.query(Module).order_by(Module.key).all()
    if not todos:
        click.echo("Nenhum módulo registrado ainda.")
        return
    for modulo in todos:
        click.echo(f"{modulo.key:12} {'on' if modulo.enabled else 'off':4} {modulo.name}")
