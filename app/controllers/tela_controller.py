"""Blueprint dos payloads de tela. Só HTTP."""
from flask import Blueprint, jsonify
from flask_jwt_extended import jwt_required

from app.controllers.autenticacao import obter_usuario_atual


def criar_blueprint_telas(servico_telas, servico_auth) -> Blueprint:
    bp = Blueprint("telas", __name__, url_prefix="/api/v1")

    @bp.get("/eu")
    @jwt_required()
    def eu():
        usuario = obter_usuario_atual(servico_auth)
        return jsonify(servico_telas.eu(usuario.id)), 200

    @bp.get("/telas/inicio")
    @jwt_required()
    def inicio():
        usuario = obter_usuario_atual(servico_auth)
        return jsonify(servico_telas.inicio(usuario.id)), 200

    return bp
