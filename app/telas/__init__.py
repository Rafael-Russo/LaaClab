from flask import Blueprint

bp = Blueprint("telas", __name__)

from app.telas import routes  # noqa: E402,F401  (registra as views no blueprint)
