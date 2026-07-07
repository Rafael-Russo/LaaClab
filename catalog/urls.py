"""URL routes for the catalogue domain: page shells, the library JSON
endpoint, and the games/genres/library REST resources under ``/api/v1/``.
"""

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from . import api, rest, views

router = DefaultRouter()
router.register("games", rest.GameViewSet)
router.register("genres", rest.GenreViewSet)
router.register("library", rest.LibraryViewSet, basename="library")

urlpatterns = [
    # Page shells
    path("explorar/", views.explore, name="explore"),
    path("biblioteca/", views.library, name="library"),

    # Per-screen JSON endpoint
    path("api/biblioteca/", api.library, name="api_library"),

    # REST CRUD API (browsable)
    path("api/v1/", include(router.urls)),
]
