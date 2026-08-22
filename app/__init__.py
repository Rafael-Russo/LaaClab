"""Application factory do LaaCLab."""
from flask import Flask, jsonify

from app.extensions import db, jwt, migrate


def create_app(config_object=None):
    app = Flask(__name__)

    if config_object is None:
        from config import get_config

        config_object = get_config()
    app.config.from_object(config_object)

    # Acentuação legível no JSON de resposta.
    app.json.ensure_ascii = False
    app.json.sort_keys = False

    db.init_app(app)
    migrate.init_app(app, db)
    jwt.init_app(app)

    # Importa os models para que o Migrate os enxergue.
    from app import models  # noqa: F401

    from app.errors import registrar_handlers

    registrar_handlers(app)
    _registrar_handlers_jwt()

    @app.get("/saude")
    def saude():
        return jsonify({"status": "ok"})

    return app


def _registrar_handlers_jwt():
    """Todo problema de token responde 401 — nunca 403."""
    from flask import jsonify

    @jwt.expired_token_loader
    def _expirado(_cabecalho, _payload):
        return jsonify({"erro": "Sessão expirada."}), 401

    @jwt.invalid_token_loader
    def _invalido(_motivo):
        return jsonify({"erro": "Autenticação necessária."}), 401

    @jwt.unauthorized_loader
    def _ausente(_motivo):
        return jsonify({"erro": "Autenticação necessária."}), 401
