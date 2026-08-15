"""Busca, ordenação e paginação — o que o DRF dava por configuração.

O envelope de resposta é **idêntico** ao do `PageNumberPagination`
(`count`/`next`/`previous`/`results`) porque o JS do front-end já lê esse
formato; qualquer diferença quebraria todas as telas de uma vez.
"""

from urllib.parse import urlencode

from flask import current_app, request
from sqlalchemy import or_


def paginar(
    query,
    *,
    search_fields: list[str] | None = None,
    ordering_fields: list[str] | None = None,
    default_ordering: str | None = None,
) -> dict:
    """Aplica `?search=`, `?ordering=` e `?page=` e devolve o envelope do DRF.

    `search_fields` e `ordering_fields` recebem nomes de coluna do model (não
    os objetos coluna); ambos servem de allowlist — buscar ou ordenar por um
    campo não declarado é ignorado em silêncio, como no DRF.

    O envelope é idêntico ao do DRF. O tratamento de `page` inválida **não**:
    o DRF levanta 404 para página fora de faixa ou não-numérica, aqui a
    primeira é `results` vazio e a segunda cai para a página 1. Escolha
    deliberada — 404 num link velho é pior que uma página vazia.

    Assume uma query de uma entidade só, sem `distinct`, `group_by` ou join
    que multiplique linha por entidade — um join desses infla o `count`.
    """
    query = _aplicar_busca(query, search_fields)
    query = _aplicar_ordenacao(query, ordering_fields, default_ordering)

    total = query.order_by(None).count()
    tamanho = current_app.config["PAGE_SIZE"]
    pagina = _pagina_pedida()

    itens = query.limit(tamanho).offset((pagina - 1) * tamanho).all()
    ultima = max(1, -(-total // tamanho))  # divisão inteira arredondando p/ cima

    return {
        "count": total,
        "next": _url_da_pagina(pagina + 1) if pagina < ultima else None,
        "previous": _url_da_pagina(pagina - 1) if pagina > 1 else None,
        "results": itens,
    }


def _entidade(query):
    return query.column_descriptions[0]["entity"]


def _aplicar_busca(query, search_fields):
    termo = (request.args.get("search") or "").strip()
    if not termo or not search_fields:
        return query
    entidade = _entidade(query)
    colunas = [getattr(entidade, nome, None) for nome in search_fields]
    colunas = [coluna for coluna in colunas if coluna is not None]
    if not colunas:
        return query
    padrao = f"%{termo}%"
    return query.filter(or_(*[coluna.ilike(padrao) for coluna in colunas]))


def _aplicar_ordenacao(query, ordering_fields, default_ordering):
    pedido = (request.args.get("ordering") or "").strip()
    permitidos = set(ordering_fields or [])
    campo = pedido.lstrip("-")
    if not campo or campo not in permitidos:
        pedido = default_ordering or ""
        campo = pedido.lstrip("-")
    if not campo:
        return query
    coluna = getattr(_entidade(query), campo, None)
    if coluna is None:
        return query
    return query.order_by(coluna.desc() if pedido.startswith("-") else coluna.asc())


def _pagina_pedida() -> int:
    try:
        pagina = int(request.args.get("page", 1))
    except (TypeError, ValueError):
        return 1
    return pagina if pagina >= 1 else 1


def _url_da_pagina(numero: int) -> str:
    """Monta a URL da página vizinha preservando os demais parâmetros.

    Usa `urlencode` em vez de concatenar: um termo de busca com `&`, espaço ou
    `+` — o que uma caixa de busca recebe todo dia — sairia corrompido numa
    query string montada à mão, e o `next` devolveria um filtro diferente do
    que o usuário pediu. `doseq=True` com `request.args.lists()` preserva
    parâmetro repetido, que o `to_dict()` engoliria.
    """
    args = [(k, v) for k, valores in request.args.lists() for v in valores if k != "page"]
    args.append(("page", str(numero)))
    return f"{request.base_url}?{urlencode(args)}"
