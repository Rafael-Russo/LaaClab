"""URL routes for the community (forum) domain: the page shell and the
per-screen JSON endpoint. The topics/replies/comments REST resources are
mounted at ``/api/v1/`` by the single router in ``config.urls``.
"""

from django.urls import path

from . import api, views

urlpatterns = [
    # Page shell
    path("comunidade/", views.community, name="community"),

    # Per-screen JSON endpoint
    path("api/comunidade/", api.community, name="api_community"),
]
