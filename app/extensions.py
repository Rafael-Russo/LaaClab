"""Extensions instanciadas sem app vinculado.

Cada uma é vinculada dentro de `create_app` via `init_app`. Manter as
instâncias aqui (e não dentro da factory) permite importá-las de qualquer
módulo de domínio sem import circular.
"""

import sqlite3

from flask_login import LoginManager
from flask_mail import Mail
from flask_migrate import Migrate
from flask_smorest import Api
from flask_sqlalchemy import SQLAlchemy
from flask_wtf.csrf import CSRFProtect
from sqlalchemy import event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Base declarativa do SQLAlchemy 2.0 usada por todos os models."""


db = SQLAlchemy(model_class=Base)
# render_as_batch: o SQLite não sabe fazer ALTER TABLE; o Alembic emula
# recriando a tabela. Necessário porque dev e testes rodam em SQLite.
migrate = Migrate(render_as_batch=True)
login_manager = LoginManager()
csrf = CSRFProtect()
mail = Mail()
api = Api()


@event.listens_for(Engine, "connect")
def _sqlite_forca_foreign_keys(dbapi_connection, connection_record):
    """Liga a checagem de foreign key no SQLite.

    O SQLite ignora foreign keys por padrão — e com isso todo
    `ondelete="CASCADE"` do projeto vira decoração em dev e nos testes, embora
    funcione em produção (o InnoDB aplica por padrão). Sem este pragma, um
    teste de cascade passa medindo o cascade do ORM e nunca o do banco.
    No-op em qualquer outro driver.
    """
    if isinstance(dbapi_connection, sqlite3.Connection):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()


@login_manager.user_loader
def _load_user(user_id):
    """Resolve o usuário da sessão. `None` quando o id não existe, não é
    inteiro ou a conta está desativada — o Flask-Login trata os três casos
    como anônimo.

    Deliberado, não incidental: `UserMixin.is_authenticated` delega para
    `self.is_active`, que aqui é coluna (não a constante `True` do mixin), e
    hoje isso já bastaria para a sessão de uma conta desativada virar
    anônima. Mas essa cadeia não está documentada em lugar nenhum e depende
    de uma versão específica do Flask-Login — então checamos aqui também,
    explicitamente, do mesmo jeito que o `ModelBackend.get_user()` do Django
    devolve `None` para conta inativa.
    """
    from app.accounts.models import User

    try:
        user = db.session.get(User, int(user_id))
    except (TypeError, ValueError):
        return None
    return user if user is not None and user.is_active else None
