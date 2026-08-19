"""URL routes for the cross-cutting shell: home, bugômetro and game-detail
page shells (server-rendered HTML) plus the per-screen JSON endpoints they
fetch from. Alerts, profile/me, forum and catalogue domains live in their own
apps (``alerts``, ``accounts``, ``community``, ``catalog``).
"""

from django.urls import path

from . import api, views

urlpatterns = [
    # PWA: service worker + manifest must live at the root scope (not under
    # /static/) so the SW's default scope covers the whole site.
    path("sw.js", views.service_worker, name="service_worker"),
    path("manifest.webmanifest", views.manifest, name="manifest"),
    path("offline/", views.offline, name="offline"),

    # Page shells
    path("", views.home, name="home"),
    path("bugometro/", views.bugometro, name="bugometro"),
    path("jogo/<slug:slug>/", views.game_detail, name="game_detail"),
    path("historicos/", views.historicos, name="historicos"),

    # Per-screen JSON endpoints (curated shapes the screens fetch)
    path("api/home/", api.home, name="api_home"),
    path("api/bugometro/", api.bugometro, name="api_bugometro"),
    path("api/jogo/<slug:slug>/", api.game_detail, name="api_game_detail"),
    path("api/historicos/", api.historicos, name="api_historicos"),
]
