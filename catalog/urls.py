"""URL routes for the catalogue domain: page shells and the library JSON
endpoint. The games/genres/library REST resources are mounted at
``/api/v1/`` by the single router in ``config.urls``.
"""

from django.urls import path

from . import api, views

urlpatterns = [
    # Page shells
    path("explorar/", views.explore, name="explore"),
    path("biblioteca/", views.library, name="library"),

    # Per-screen JSON endpoint
    path("api/biblioteca/", api.library, name="api_library"),
]
