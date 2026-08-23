"""Blueprint de autenticação. Único lugar que emite token."""
from flask import Blueprint, jsonify, request
from flask_jwt_extended import (
    create_access_token,
    create_refresh_token,
    get_jwt_identity,
    jwt_required,
)

from app.controllers.autenticacao import obter_usuario_atual


def criar_blueprint_auth(servico_auth) -> Blueprint:
    bp = Blueprint("auth", __name__, url_prefix="/api/auth")

    def _tokens(usuario_id: int) -> dict:
        identidade = str(usuario_id)
        return {
            "token_acesso": create_access_token(identity=identidade),
            "token_renovacao": create_refresh_token(identity=identidade),
        }

    @bp.post("/registro")
    def registro():
        usuario, status = servico_auth.registrar(request.get_json(silent=True) or {})
        return jsonify({"usuario": usuario, **_tokens(usuario["id"])}), status

    @bp.post("/login")
    def login():
        usuario, status = servico_auth.autenticar(request.get_json(silent=True) or {})
        return jsonify({"usuario": usuario, **_tokens(usuario["id"])}), status

    @bp.post("/renovar")
    @jwt_required(refresh=True)
    def renovar():
        identidade = get_jwt_identity()
        return jsonify(
            {"token_acesso": create_access_token(identity=identidade)}
        ), 200

    @bp.post("/senha")
    @jwt_required()
    def trocar_senha():
        usuario = obter_usuario_atual(servico_auth)
        servico_auth.trocar_senha(usuario.id, request.get_json(silent=True) or {})
        # Tokens novos: sem eles a pessoa seria deslogada pela própria
        # revogação que acabou de acionar.
        return jsonify(_tokens(usuario.id)), 200

    return bp
