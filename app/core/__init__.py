"""Blueprint do núcleo. Na fatia 1a só existe a home, como destino dos
redirects de login/signup; as telas de verdade chegam na 1b."""

from flask import Blueprint
from flask_login import login_required

bp = Blueprint("core", __name__)


@bp.get("/")
@login_required
def home():
    return "LaaCLab"
