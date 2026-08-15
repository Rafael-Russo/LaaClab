"""App factory do LaaCLab."""

from flask import Flask, jsonify
from whitenoise import WhiteNoise

from app.celery_app import celery_init_app
from app.config import BaseConfig, get_config
from app.extensions import api, csrf, db, login_manager, mail, migrate
from app.security import register_host_check


def create_app(config: BaseConfig | None = None) -> Flask:
    app = Flask(__name__, static_folder="static", template_folder="templates")
    app.config.from_object(config or get_config())

    _register_extensions(app)
    celery_init_app(app)
    register_host_check(app)
    _register_blueprints(app)

    @app.get("/healthz")
    def healthz():
        """Liveness probe — usada pelo compose e pelo nginx."""
        return jsonify({"status": "ok"})

    _register_static(app)
    return app


def _register_extensions(app: Flask) -> None:
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    csrf.init_app(app)
    mail.init_app(app)
    # Monta /api/v1/openapi.json e o Swagger UI em /api/v1/docs. Fica vazio
    # até a fatia 1 registrar o primeiro recurso.
    api.init_app(app)


def _register_blueprints(app: Flask) -> None:
    """Os blueprints de domínio chegam a partir da fatia 1."""


def _register_static(app: Flask) -> None:
    """Fora de debug, o WhiteNoise serve /static/ direto do WSGI.

    É middleware WSGI puro — independe de framework, e por isso sobrevive à
    saída do Django. Em debug o Flask serve sozinho, com recarga imediata.
    """
    if app.debug or app.testing:
        return
    app.wsgi_app = WhiteNoise(
        app.wsgi_app,
        root=str(app.static_folder),
        prefix=app.static_url_path.lstrip("/") + "/",
        autorefresh=False,
    )
