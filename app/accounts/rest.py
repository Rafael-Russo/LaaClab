"""Recurso `/api/v1/me/` — o perfil do usuário autenticado."""

from flask.views import MethodView
from flask_login import current_user
from flask_smorest import Blueprint

from app.accounts.schemas import UserProfileSchema
from app.core.decorators import api_login_required
from app.extensions import db

bp = Blueprint(
    "me", __name__, url_prefix="/api/v1/me", description="Perfil do usuário autenticado"
)


@bp.route("/")
class MeView(MethodView):
    @api_login_required
    @bp.response(200, UserProfileSchema)
    def get(self):
        return current_user.profile

    @api_login_required
    @bp.arguments(UserProfileSchema())
    @bp.response(200, UserProfileSchema)
    def patch(self, dados):
        perfil = current_user.profile
        for campo, valor in dados.items():
            setattr(perfil, campo, valor)
        db.session.commit()
        return perfil
