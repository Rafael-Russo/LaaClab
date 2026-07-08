"""URL routes for the accounts domain: the page shell, the per-screen JSON
endpoints, and the profile REST resource under ``/api/v1/``.
"""

from django.urls import path

from . import api, rest, views

urlpatterns = [
    # Page shell
    path("perfil/", views.profile, name="profile"),

    # Per-screen JSON endpoints
    path("api/perfil/", api.profile, name="api_profile"),
    path("api/me/", api.me, name="api_me"),

    # REST CRUD API (browsable)
    path("api/v1/me/", rest.MeView.as_view(), name="api_me_profile"),
]
