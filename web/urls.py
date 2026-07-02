"""URL routes for the web-visualization module.

Two groups: page shells (server-rendered HTML) and the ``/api/`` JSON
endpoints the pages fetch from.
"""

from django.urls import path

from . import api, views

urlpatterns = [
    # Page shells
    path("", views.home, name="home"),
    path("bugometro/", views.bugometro, name="bugometro"),
    path("biblioteca/", views.library, name="library"),
    path("comunidade/", views.community, name="community"),
    path("alertas/", views.alerts, name="alerts"),
    path("perfil/", views.profile, name="profile"),
    path("jogo/<slug:slug>/", views.game_detail, name="game_detail"),

    # JSON endpoints
    path("api/me/", api.me, name="api_me"),
    path("api/home/", api.home, name="api_home"),
    path("api/bugometro/", api.bugometro, name="api_bugometro"),
    path("api/biblioteca/", api.library, name="api_library"),
    path("api/comunidade/", api.community, name="api_community"),
    path("api/alertas/", api.alerts, name="api_alerts"),
    path("api/perfil/", api.profile, name="api_profile"),
    path("api/jogo/<slug:slug>/", api.game_detail, name="api_game_detail"),
]
