"""Comandos de linha de comando.

Portam os `management/commands` do Django. Todos idempotentes: rodar duas
vezes deixa o mesmo estado, porque o `entrypoint.sh` os chama a cada boot.
"""

import click
from flask import Flask

from app.accounts.models import Role, User, UserProfile
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

# `catalog`, `community` e `alerts` têm link na navegação (ver
# `MODULE_CANDIDATES`); `accounts` e `bugs` não, mas são togglable do mesmo
# jeito — o Django os semeia igual, e `module_enabled("bugs")` sozinho já é
# consultado 6 vezes em `bugs/rest.py`. `flask modules --list` precisa
# mostrar os cinco para o operador conseguir ligar/desligar qualquer um.
NOMES_DE_MODULO = {
    "catalog": "Catálogo",
    "community": "Comunidade",
    "alerts": "Alertas",
    "accounts": "Contas",
    "bugs": "BugoMetro",
}

DEMO_USERNAME = "gamer"
DEMO_PASSWORD = "gamerpass123"


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

    _seed_usuario_demo()
    click.echo("Seed concluído.")


def _seed_usuario_demo() -> None:
    """Fetch-or-create do usuário de demonstração e do seu perfil.

    A senha é sempre redefinida, mesmo quando o usuário já existe — igual ao
    comentário do comando Django ("Always (re)set the documented demo
    password so login works after seed"): sem isso, uma senha alterada (ou
    nunca definida, se o usuário tivesse nascido por outro caminho) deixaria
    o login de demonstração documentado no README parado de funcionar.
    """
    gamer = db.session.query(User).filter_by(username=DEMO_USERNAME).first()
    if gamer is None:
        gamer = User(username=DEMO_USERNAME, email="gamer@laaclab.example")
        db.session.add(gamer)
    gamer.set_password(DEMO_PASSWORD)
    db.session.commit()

    # `_criar_perfil` (evento `after_insert` de `User`) já garante um perfil
    # vazio; aqui só preenchemos os campos de demonstração que a tela de
    # perfil da fatia 1b foi desenhada em cima de.
    perfil = gamer.profile
    if perfil is None:
        perfil = UserProfile(user_id=gamer.id, handle=DEMO_USERNAME)
        db.session.add(perfil)
    perfil.handle = "Nikola98"
    perfil.level = 12
    perfil.xp = 1250
    perfil.achievements = 24
    perfil.friends = 8
    perfil.days_active = 47
    perfil.bio = "Jogando, aprendendo e evoluindo todos os dias."
    db.session.commit()

    click.echo(f"Usuário de demonstração: {DEMO_USERNAME} / {DEMO_PASSWORD}")


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
