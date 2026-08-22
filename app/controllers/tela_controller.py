"""Blueprint dos payloads de tela. Só HTTP."""
from flask import Blueprint, jsonify, request
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

    @bp.get("/telas/bugometro")
    @jwt_required()
    def bugometro():
        usuario = obter_usuario_atual(servico_auth)
        slug = request.args.get("jogo")
        return jsonify(servico_telas.bugometro(slug=slug, usuario=usuario)), 200

    @bp.get("/telas/jogo/<slug>")
    @jwt_required()
    def jogo(slug):
        usuario = obter_usuario_atual(servico_auth)
        return jsonify(servico_telas.jogo(slug, usuario=usuario)), 200

    @bp.get("/telas/biblioteca")
    @jwt_required()
    def biblioteca():
        usuario = obter_usuario_atual(servico_auth)
        return jsonify(servico_telas.biblioteca(usuario.id)), 200

    @bp.get("/telas/perfil")
    @jwt_required()
    def perfil():
        usuario = obter_usuario_atual(servico_auth)
        return jsonify(servico_telas.perfil(usuario.id)), 200

    return bp
