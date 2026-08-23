"""Fábrica de blueprints CRUD.

Substitui o crud.py antigo, que fundia controller, service e repository na
mesma função. Aqui só existe HTTP: ler a requisição, chamar o Service,
escolher o status. Nenhum db.session, nenhum model.
"""
from urllib.parse import urlencode

from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required

from app.controllers.autenticacao import (
    obter_usuario_atual,
    obter_usuario_opcional,
)

POR_PAGINA_PADRAO = 20


def montar_link(caminho: str, pagina: int, por_pagina: int) -> str:
    """Preserva os demais parâmetros da consulta.

    Sem isso, seguir `proxima` perderia o `ordenar_por` e a página 2
    voltaria à ordem padrão — misturando resultados fora de ordem entre
    as páginas do "Carregar mais".
    """
    parametros = [("pagina", pagina), ("por_pagina", por_pagina)]
    parametros += sorted(
        (chave, valor)
        for chave, valor in request.args.items()
        if chave not in ("pagina", "por_pagina")
    )
    return f"{caminho}?{urlencode(parametros)}"


def criar_controller_crud(
    nome: str,
    servico,
    prefixo: str,
    servico_auth,
    sem_criacao: bool = False,
    sem_atualizacao: bool = False,
) -> Blueprint:
    """Gera as rotas REST. Leitura pública, escrita exige JWT.

    `sem_criacao` e `sem_atualizacao` omitem POST e PUT/PATCH quando o
    recurso não tem uso para eles — ex.: `/usuarios` (criar é
    `/api/auth/registro`) e `/votos-bug` (nada nele é atualizável depois
    do bloqueio de troca de `relato_id`). Sem rota registrada, o Flask
    responde 405 sozinho.
    """
    caminho = f"/api/v1/{prefixo}"
    bp = Blueprint(nome, __name__, url_prefix=caminho)

    @bp.get("")
    @bp.get("/")
    def listar():
        pagina = request.args.get("pagina", 1, type=int)
        por_pagina = request.args.get("por_pagina", POR_PAGINA_PADRAO, type=int)
        ordenar_por = request.args.get("ordenar_por")
        # Leitura é pública, mas o Service precisa saber se quem lê é
        # admin para decidir sobre conteúdo moderado (spec 4.8).
        usuario = obter_usuario_opcional(servico_auth)

        resultado = servico.listar(
            pagina=pagina,
            por_pagina=por_pagina,
            ordenar_por=ordenar_por,
            usuario=usuario,
        )
        # proxima/anterior são caminhos relativos: o explore.js faz fetch
        # direto neles ao percorrer as páginas de gêneros.
        resultado["proxima"] = (
            montar_link(caminho, resultado["pagina"] + 1, resultado["por_pagina"])
            if resultado["pagina"] < resultado["paginas"]
            else None
        )
        resultado["anterior"] = (
            montar_link(caminho, resultado["pagina"] - 1, resultado["por_pagina"])
            if resultado["pagina"] > 1
            else None
        )
        return jsonify(resultado), 200

    @bp.get("/<int:identificador>")
    def detalhar(identificador):
        usuario = obter_usuario_opcional(servico_auth)
        return jsonify(servico.obter(identificador, usuario=usuario)), 200

    if not sem_criacao:

        @bp.post("")
        @bp.post("/")
        @jwt_required()
        def criar():
            usuario = obter_usuario_atual(servico_auth)
            dados = request.get_json(silent=True) or {}
            criado = servico.criar(dados, usuario=usuario)
            return jsonify(criado), 201

    if not sem_atualizacao:

        @bp.put("/<int:identificador>")
        @bp.patch("/<int:identificador>")
        @jwt_required()
        def atualizar(identificador):
            usuario = obter_usuario_atual(servico_auth)
            dados = request.get_json(silent=True) or {}
            return jsonify(servico.atualizar(identificador, dados, usuario)), 200

    @bp.delete("/<int:identificador>")
    @jwt_required()
    def remover(identificador):
        usuario = obter_usuario_atual(servico_auth)
        servico.remover(identificador, usuario)
        return "", 204

    return bp
