from flask import Blueprint
from flask_login import login_required

bp = Blueprint("telas", __name__)


@bp.before_request
@login_required
def exigir_login():
    """Toda tela exige sessão. Vale também para rotas criadas em F3–F6."""


from app.telas import routes  # noqa: E402,F401  (registra as views no blueprint)
