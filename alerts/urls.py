"""URL routes for the alerts domain: the page shell, the per-screen JSON
endpoint, and the alerts REST resource under ``/api/v1/``.
"""

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from . import api, rest, views

router = DefaultRouter()
router.register("alerts", rest.AlertViewSet)

urlpatterns = [
    # Page shell
    path("alertas/", views.alerts, name="alerts"),

    # Per-screen JSON endpoint
    path("api/alertas/", api.alerts, name="api_alerts"),

    # REST CRUD API (browsable)
    path("api/v1/", include(router.urls)),
]
