"""URL routes for the community (forum) domain: the page shell, the
per-screen JSON endpoint, and the topics/replies/comments REST resources
under ``/api/v1/``.
"""

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from . import api, rest, views

router = DefaultRouter()
router.register("topics", rest.TopicViewSet)
router.register("replies", rest.ReplyViewSet)
router.register("comments", rest.GameCommentViewSet)

urlpatterns = [
    # Page shell
    path("comunidade/", views.community, name="community"),

    # Per-screen JSON endpoint
    path("api/comunidade/", api.community, name="api_community"),

    # REST CRUD API (browsable)
    path("api/v1/", include(router.urls)),
]
