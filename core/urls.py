"""URL routes for the cross-cutting shell: home, bugômetro and game-detail
page shells (server-rendered HTML) plus the per-screen JSON endpoints they
fetch from. Alerts, profile/me, forum and catalogue domains live in their own
apps (``alerts``, ``accounts``, ``community``, ``catalog``).
"""

from django.urls import path

from . import api, views

urlpatterns = [
    # Page shells
    path("", views.home, name="home"),
    path("bugometro/", views.bugometro, name="bugometro"),
    path("jogo/<slug:slug>/", views.game_detail, name="game_detail"),

    # Per-screen JSON endpoints (curated shapes the screens fetch)
    path("api/home/", api.home, name="api_home"),
    path("api/bugometro/", api.bugometro, name="api_bugometro"),
    path("api/jogo/<slug:slug>/", api.game_detail, name="api_game_detail"),
]
