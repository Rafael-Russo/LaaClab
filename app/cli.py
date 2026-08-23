"""Comandos de linha de comando.

O bootstrap do primeiro administrador não pode ser uma rota: qualquer
rota capaz de conceder privilégio é uma rota capaz de ser abusada. Aqui
exige acesso ao servidor, que é a credencial certa para esta operação.
"""
import click
from flask.cli import with_appcontext


def registrar_comandos(app):
    app.cli.add_command(promover)
    app.cli.add_command(seed_db)


@click.command("promover")
@click.argument("nome_usuario")
@with_appcontext
def promover(nome_usuario):
    """Torna um usuário existente administrador."""
    from app.extensions import db
    from app.models import Usuario

    usuario = db.session.execute(
        db.select(Usuario).where(Usuario.nome_usuario == nome_usuario)
    ).scalars().first()

    if usuario is None:
        raise click.ClickException(f"Usuário '{nome_usuario}' não existe.")

    usuario.is_admin = True
    db.session.commit()
    click.echo(f"'{nome_usuario}' agora é administrador.")


@click.command("seed-db")
@with_appcontext
def seed_db():
    """Popula o banco com conteúdo de demonstração."""
    from app.seed import semear

    click.echo("Semeando o banco...")
    semear()
    click.echo("Pronto.")
