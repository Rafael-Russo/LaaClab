"""Extensions instanciadas sem app vinculado.

Cada uma é vinculada dentro de `create_app` via `init_app`. Manter as
instâncias aqui (e não dentro da factory) permite importá-las de qualquer
módulo de domínio sem import circular.
"""

from flask_login import LoginManager
from flask_mail import Mail
from flask_migrate import Migrate
from flask_smorest import Api
from flask_sqlalchemy import SQLAlchemy
from flask_wtf.csrf import CSRFProtect
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


@login_manager.user_loader
def _load_user(user_id):
    """Resolve o usuário da sessão. `None` quando o id não existe ou não é
    inteiro — o Flask-Login trata os dois casos como anônimo."""
    from app.accounts.models import User

    try:
        return db.session.get(User, int(user_id))
    except (TypeError, ValueError):
        return None
