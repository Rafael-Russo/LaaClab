"""URL routes for the alerts domain: the page shell and the per-screen JSON
endpoint. The alerts REST resource is mounted at ``/api/v1/`` by the single
router in ``config.urls``.
"""

from django.urls import path

from . import api, views

urlpatterns = [
    # Page shell
    path("alertas/", views.alerts, name="alerts"),

    # Per-screen JSON endpoint
    path("api/alertas/", api.alerts, name="api_alerts"),
]
