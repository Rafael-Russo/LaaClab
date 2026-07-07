"""URL routes for the web-visualization module.

Three groups: page shells (server-rendered HTML), the per-screen JSON endpoints
the pages fetch from, and the REST CRUD API under ``/api/v1/``.
"""

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from . import api, rest, views

router = DefaultRouter()
router.register("alerts", rest.AlertViewSet)
router.register("topics", rest.TopicViewSet)
router.register("replies", rest.ReplyViewSet)
router.register("comments", rest.GameCommentViewSet)

urlpatterns = [
    # Page shells
    path("", views.home, name="home"),
    path("bugometro/", views.bugometro, name="bugometro"),
    path("comunidade/", views.community, name="community"),
    path("alertas/", views.alerts, name="alerts"),
    path("perfil/", views.profile, name="profile"),
    path("jogo/<slug:slug>/", views.game_detail, name="game_detail"),

    # Per-screen JSON endpoints (curated shapes the screens fetch)
    path("api/me/", api.me, name="api_me"),
    path("api/home/", api.home, name="api_home"),
    path("api/bugometro/", api.bugometro, name="api_bugometro"),
    path("api/comunidade/", api.community, name="api_community"),
    path("api/alertas/", api.alerts, name="api_alerts"),
    path("api/perfil/", api.profile, name="api_profile"),
    path("api/jogo/<slug:slug>/", api.game_detail, name="api_game_detail"),

    # REST CRUD API (browsable)
    path("api/v1/me/", rest.MeView.as_view(), name="api_me_profile"),
    path("api/v1/", include(router.urls)),
]
