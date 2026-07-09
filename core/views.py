"""Page (shell) views. Each renders a static HTML template that then fetches
its data from the JSON endpoints in ``api.py``. All pages require login."""

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import render
from django.templatetags.static import static
from django.views.decorators.cache import cache_control


def manifest(request):
    """PWA manifest (installability): served at the root scope so the
    ``start_url``/``scope`` apply to the whole site."""
    return JsonResponse({
        "name": "LaaCLab", "short_name": "LaaCLab",
        "start_url": "/", "display": "standalone",
        "background_color": "#0a0b12", "theme_color": "#e01e2b",
        "icons": [
            {"src": static("web/img/icon-192.png"), "sizes": "192x192", "type": "image/png"},
            {"src": static("web/img/icon-512.png"), "sizes": "512x512", "type": "image/png"},
        ],
    }, content_type="application/manifest+json")


@cache_control(max_age=0)
def service_worker(request):
    """Service worker script: must be served at ``/sw.js`` (root scope) for
    its default scope to cover the whole site. ``max_age=0`` so browsers
    always revalidate it and pick up new precache versions promptly."""
    return render(request, "web/sw.js", content_type="application/javascript",
                  context={"version": "v1"})


def offline(request):
    """Offline fallback page, precached by the service worker and served for
    failed navigations while offline."""
    return render(request, "web/offline.html")


@login_required
def home(request):
    return render(request, "web/home.html", {"active": "home"})


@login_required
def bugometro(request):
    return render(request, "web/bugometro.html", {"active": "bugometro"})


@login_required
def game_detail(request, slug):
    return render(request, "web/game_detail.html", {"active": "home", "slug": slug})


@login_required
def historicos(request):
    return render(request, "web/historicos.html", {"active": "historicos"})
