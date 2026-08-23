"""Exceções de domínio e a tradução delas para HTTP.

As classes NÃO importam Flask: é isso que permite a camada Service
levantá-las sem violar a regra de camadas. Só ``registrar_handlers``
conhece Flask, e ela é chamada pelo factory.
"""


class ErroDeDominio(Exception):
    """Base de todo erro previsto do domínio."""

    status = 500

    def __init__(self, mensagem: str, erros: dict | None = None):
        super().__init__(mensagem)
        self.mensagem = mensagem
        self.erros = erros


class NaoAutorizado(ErroDeDominio):
    """Sem credencial válida. SEMPRE 401 — nunca 403 — senão o front não
    redireciona para o login."""

    status = 401


class AcessoNegado(ErroDeDominio):
    """Autenticado, mas não é dono do recurso nem administrador."""

    status = 403


class NaoEncontrado(ErroDeDominio):
    status = 404


class Conflito(ErroDeDominio):
    """Violação de unicidade (nome_usuario, email, voto duplicado...)."""

    status = 409


class DadosInvalidos(ErroDeDominio):
    """Falha de validação de schema. ``erros`` traz o dicionário campo→lista."""

    status = 422


def registrar_handlers(app):
    """Traduz exceção de domínio em resposta JSON. Chamado pelo factory."""
    from flask import jsonify

    from app.extensions import db

    @app.errorhandler(ErroDeDominio)
    def _dominio(erro: ErroDeDominio):
        if erro.erros is not None:
            return jsonify({"erros": erro.erros}), erro.status
        return jsonify({"erro": erro.mensagem}), erro.status

    @app.errorhandler(404)
    def _nao_encontrado(_e):
        return jsonify({"erro": "Recurso não encontrado."}), 404

    @app.errorhandler(405)
    def _metodo(_e):
        return jsonify({"erro": "Método não permitido."}), 405

    @app.errorhandler(500)
    def _interno(_e):
        db.session.rollback()
        return jsonify({"erro": "Erro interno do servidor."}), 500
