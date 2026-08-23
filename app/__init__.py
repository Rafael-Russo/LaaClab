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

    from app.composicao import montar_servicos
    from app.controllers.auth_controller import criar_blueprint_auth
    from app.controllers.paginas_controller import criar_blueprint_midia
    from app.controllers.registro import registrar_controllers

    servicos = montar_servicos()
    app.extensions["servicos_laaclab"] = servicos
    app.register_blueprint(criar_blueprint_auth(servicos.auth))
    app.register_blueprint(criar_blueprint_midia())
    registrar_controllers(app, servicos)

    from app.controllers.tela_controller import criar_blueprint_telas

    app.register_blueprint(criar_blueprint_telas(servicos.telas, servicos.auth))

    from app.controllers.web_controller import criar_blueprint_web

    app.register_blueprint(criar_blueprint_web())

    @app.get("/saude")
    def saude():
        return jsonify({"status": "ok"})

    from app.cli import registrar_comandos

    registrar_comandos(app)

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

    @jwt.additional_claims_loader
    def _versao_da_sessao(identidade):
        """Carimba no token a versão de sessão do usuário no momento da
        emissão. Roda em toda criação de token, inclusive na renovação."""
        from app.extensions import db
        from app.models import Usuario

        usuario = db.session.get(Usuario, int(identidade))  # guarda: excecao declarada
        return {"versao_sessao": usuario.versao_sessao if usuario else 0}

    @jwt.token_in_blocklist_loader
    def _revogado(_cabecalho, payload):
        """Token de uma versão de sessão anterior não vale mais.

        JWT não se revoga: sem isto, trocar a senha não invalidaria o
        refresh de 7 dias já emitido, e quem trocasse justamente porque a
        senha vazou continuaria com o invasor dentro por uma semana.

        Compara VERSÃO, não relógio: o `iat` é inteiro em segundos, e o
        token emitido pela própria troca nasce no mesmo segundo da marca.
        """
        from app.extensions import db
        from app.models import Usuario

        usuario = db.session.get(Usuario, int(payload["sub"]))  # guarda: excecao declarada
        if usuario is None:
            # Conta apagada: o token não tem mais dono. Sem isto,
            # /api/auth/renovar segue cunhando access token por até 7
            # dias para uma conta que não existe.
            return True
        # O default `0` é carência de migração: tokens emitidos antes
        # deste recurso não têm a claim e não devem deslogar ninguém.
        # Depois de 7 dias em produção (validade máxima do refresh)
        # nenhum token assim existe, e o default vira falha aberta —
        # trocar por `payload.get("versao_sessao")` sem default, que
        # recusa o token quando a claim falta por qualquer motivo.
        return payload.get("versao_sessao", 0) != usuario.versao_sessao

    @jwt.revoked_token_loader
    def _token_revogado(_cabecalho, _payload):
        return jsonify({"erro": "Sessão encerrada. Entre de novo."}), 401
