"""DRF viewsets for the bugs CRUD API (mounted at ``/api/v1/`` — see the
single router in ``config.urls``).

Regular users can list/read bugs, report new ones and vote to confirm them;
only games moderators (or staff) can confirm/reject/resolve a bug.
"""

from django.utils import timezone
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from core.gating import ModuleEnabled
from core.permissions import IsGamesModerator

from .models import Bug, BugReport, BugVote
from .serializers import BugReportSerializer, BugSerializer, BugVoteSerializer


class BugViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Bug.objects.select_related("game").all()
    serializer_class = BugSerializer
    permission_classes = [ModuleEnabled("bugs"), IsAuthenticated]
    filterset_fields = ["game__slug", "status", "category"]
    ordering_fields = ["confirmations", "created_at", "severity"]

    def _moderate(self, request, new_status):
        bug = self.get_object()
        bug.status = new_status
        bug.moderated_by = request.user
        bug.moderated_at = timezone.now()
        bug.save()
        return Response({"status": bug.status})

    @action(detail=True, methods=["post"], permission_classes=[ModuleEnabled("bugs"), IsGamesModerator])
    def confirm(self, request, pk=None):
        return self._moderate(request, Bug.Status.CONFIRMED)

    @action(detail=True, methods=["post"], permission_classes=[ModuleEnabled("bugs"), IsGamesModerator])
    def reject(self, request, pk=None):
        return self._moderate(request, Bug.Status.REJECTED)

    @action(detail=True, methods=["post"], permission_classes=[ModuleEnabled("bugs"), IsGamesModerator])
    def resolve(self, request, pk=None):
        return self._moderate(request, Bug.Status.RESOLVED)


class BugReportViewSet(viewsets.ModelViewSet):
    """Create-only: reports are fire-and-forget, there is no UI to edit/delete
    them, so list/retrieve/update/delete are disabled (405) and the queryset
    is scoped to the requesting user's own reports as a defensive backstop."""

    serializer_class = BugReportSerializer
    permission_classes = [ModuleEnabled("bugs"), IsAuthenticated]
    http_method_names = ["post", "head", "options"]

    def get_queryset(self):
        return BugReport.objects.filter(author=self.request.user).select_related("game", "author", "bug")

    def perform_create(self, serializer):
        report = serializer.save(author=self.request.user)
        if report.bug_id is None:
            bug = Bug.objects.create(
                game=report.game,
                title=report.text[:60] or "Bug reportado",
                category=report.category,
                source=Bug.Source.COMMUNITY,
            )
            report.bug = bug
            report.save(update_fields=["bug"])


class BugVoteViewSet(viewsets.ModelViewSet):
    serializer_class = BugVoteSerializer
    permission_classes = [ModuleEnabled("bugs"), IsAuthenticated]
    http_method_names = ["post", "delete", "head", "options"]

    def get_queryset(self):
        return BugVote.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        vote, _ = BugVote.objects.get_or_create(
            bug=serializer.validated_data["bug"], user=self.request.user
        )
        serializer.instance = vote
