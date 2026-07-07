from functools import wraps

from django.http import Http404

from core.models import module_enabled


def require_module(key):
    """404 a view when its module is disabled."""

    def deco(view):
        @wraps(view)
        def wrapper(request, *args, **kwargs):
            if not module_enabled(key):
                raise Http404("módulo desativado")
            return view(request, *args, **kwargs)

        return wrapper

    return deco
