"""URL routes for the web-visualization module.

Two groups: page shells (server-rendered HTML) and the per-screen JSON
endpoints the pages fetch from. Alerts, profile/me and the forum/catalogue
domains now live in their own apps (``alerts``, ``accounts``, ``community``,
``catalog``).
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
