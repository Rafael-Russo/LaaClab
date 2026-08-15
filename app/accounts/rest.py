"""Recurso `/api/v1/me/` — o perfil do usuário autenticado."""

from flask.views import MethodView
from flask_login import current_user
from flask_smorest import Blueprint

from app.accounts.models import UserProfile
from app.accounts.schemas import UserProfileSchema
from app.core.decorators import api_login_required
from app.extensions import db

bp = Blueprint(
    "me", __name__, url_prefix="/api/v1/me", description="Perfil do usuário autenticado"
)


def _perfil_do_usuario() -> UserProfile:
    """Fetch-or-create do perfil do usuário logado.

    `_criar_perfil` (evento `after_insert` em `User`) já garante um perfil
    para toda conta nova, mas nem toda conta neste banco necessariamente
    passou por ele — o `seed`, por exemplo, roda antes deste código existir
    em alguns ambientes, e uma conta antiga pode ter perdido o perfil por
    fora do ORM. Sem este fallback, `current_user.profile` é `None` e o GET
    devolve `200 {}` e o PATCH um 500 em `setattr(None, ...)`. O
    `MeView.get_object()` do Django usava `get_or_create` de propósito pelo
    mesmo motivo.
    """
    if current_user.profile is not None:
        return current_user.profile
    perfil = UserProfile(user_id=current_user.id, handle=current_user.username)
    db.session.add(perfil)
    db.session.commit()  # expira `current_user.profile`; a próxima leitura já acha a linha nova
    return perfil


@bp.route("/")
class MeView(MethodView):
    @api_login_required
    @bp.response(200, UserProfileSchema)
    def get(self):
        return _perfil_do_usuario()

    @api_login_required
    @bp.arguments(UserProfileSchema())
    @bp.response(200, UserProfileSchema)
    def patch(self, dados):
        perfil = _perfil_do_usuario()
        for campo, valor in dados.items():
            setattr(perfil, campo, valor)
        db.session.commit()
        return perfil
