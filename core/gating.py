from functools import wraps

from django.http import Http404, JsonResponse
from rest_framework.permissions import BasePermission

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


def require_module_api(key):
    """JSON 404 for plain @api_login_required endpoints when the module is off."""

    def deco(view):
        @wraps(view)
        def wrapper(request, *args, **kwargs):
            if not module_enabled(key):
                return JsonResponse({"detail": "módulo desativado"}, status=404)
            return view(request, *args, **kwargs)

        return wrapper

    return deco


def ModuleEnabled(key):
    """DRF permission: denies (403) when the given module is disabled."""

    class _ModuleEnabled(BasePermission):
        def has_permission(self, request, view):
            return module_enabled(key)

    return _ModuleEnabled
