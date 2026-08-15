"""Decorators de autorização.

Substituem as `permission_classes` do DRF e os decorators de gating do Django.
Como decorators (e não classes de permissão), servem igualmente às páginas, aos
endpoints JSON de tela e aos recursos da API v1.
"""

from functools import wraps

from flask import abort, jsonify
from flask_login import current_user

from app.core.models import module_enabled


def api_login_required(view):
    """Como `login_required`, mas devolve 401 JSON em vez de redirecionar.

    O front-end faz `fetch` nestes endpoints e precisa distinguir "não
    autenticado" de "recebi o HTML da tela de login".
    """

    @wraps(view)
    def wrapper(*args, **kwargs):
        if not current_user.is_authenticated:
            return jsonify({"detail": "Autenticação necessária."}), 401
        return view(*args, **kwargs)

    return wrapper


def staff_required(view):
    @wraps(view)
    def wrapper(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_staff:
            abort(403)
        return view(*args, **kwargs)

    return wrapper


def perm_required(perm: str):
    """403 quando o usuário não tem a permissão. Staff passa sempre."""

    def deco(view):
        @wraps(view)
        def wrapper(*args, **kwargs):
            if not current_user.is_authenticated or not current_user.has_perm(perm):
                abort(403)
            return view(*args, **kwargs)

        return wrapper

    return deco


def module_required(key: str):
    """404 numa página cujo módulo está desligado — a tela deixa de existir."""

    def deco(view):
        @wraps(view)
        def wrapper(*args, **kwargs):
            if not module_enabled(key):
                abort(404, description="módulo desativado")
            return view(*args, **kwargs)

        return wrapper

    return deco


def module_required_api(key: str):
    """404 em JSON, para os endpoints de tela consumidos por `fetch`."""

    def deco(view):
        @wraps(view)
        def wrapper(*args, **kwargs):
            if not module_enabled(key):
                return jsonify({"detail": "módulo desativado"}), 404
            return view(*args, **kwargs)

        return wrapper

    return deco


def module_required_v1(key: str):
    """403 nos recursos da API v1 cujo módulo está desligado.

    Difere do `module_required_api` de propósito: numa tela, módulo desligado
    significa que a página não existe (404); num recurso da API v1, o recurso
    existe e o acesso é que está negado (403). A spec fixa essa semântica, e
    o `ModuleEnabled` do DRF que ela substitui faz o mesmo.
    """

    def deco(view):
        @wraps(view)
        def wrapper(*args, **kwargs):
            if not module_enabled(key):
                abort(403, description="módulo desativado")
            return view(*args, **kwargs)

        return wrapper

    return deco
