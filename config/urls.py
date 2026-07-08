"""Root URL configuration for the LaaCLab project."""

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from rest_framework.routers import DefaultRouter

from alerts import rest as alerts_rest
from bugs import rest as bugs_rest
from catalog import rest as catalog_rest
from community import rest as community_rest

# Single DRF router for the whole project, mounted at ``/api/v1/`` — one
# browsable root listing every resource instead of one router per app.
router = DefaultRouter()
router.register("games", catalog_rest.GameViewSet)
router.register("genres", catalog_rest.GenreViewSet)
router.register("library", catalog_rest.LibraryViewSet, basename="library")
router.register("topics", community_rest.TopicViewSet)
router.register("replies", community_rest.ReplyViewSet)
router.register("comments", community_rest.GameCommentViewSet)
router.register("alerts", alerts_rest.AlertViewSet)
router.register("bugs", bugs_rest.BugViewSet)
router.register("bug-reports", bugs_rest.BugReportViewSet, basename="bug-reports")
router.register("bug-votes", bugs_rest.BugVoteViewSet, basename="bug-votes")

urlpatterns = [
    path("admin/", admin.site.urls),
    path("accounts/", include("allauth.urls")),
    path("api/v1/", include(router.urls)),
    path("", include("core.urls")),
    path("", include("catalog.urls")),
    path("", include("community.urls")),
    path("", include("alerts.urls")),
    path("", include("accounts.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
