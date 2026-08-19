"""URL routes for the community (forum) domain: the page shell and the
per-screen JSON endpoint. The topics/replies/comments REST resources are
mounted at ``/api/v1/`` by the single router in ``config.urls``.
"""

from django.urls import path

from . import api, views

urlpatterns = [
    # Page shells
    path("comunidade/", views.community, name="community"),
    path("comunidade/topico/<int:pk>/", views.thread, name="topic_thread"),

    # Per-screen JSON endpoints
    path("api/comunidade/", api.community, name="api_community"),
    path("api/topico/<int:pk>/", api.thread, name="api_thread"),
]
