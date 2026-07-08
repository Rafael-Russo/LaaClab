"""Reusable DRF permissions."""

from rest_framework import permissions


class IsAdminOrReadOnly(permissions.BasePermission):
    """Any authenticated user can read; only staff can write.

    Used for the catalogue (games/genres) and alerts, which regular users
    should not be able to mutate.
    """

    def has_permission(self, request, view):
        if not (request.user and request.user.is_authenticated):
            return False
        if request.method in permissions.SAFE_METHODS:
            return True
        return request.user.is_staff


class IsAuthorOrReadOnly(permissions.BasePermission):
    """Object owner (``author`` or ``user``) — or staff — may edit/delete."""

    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated)

    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True
        owner_id = getattr(obj, "author_id", None)
        if owner_id is None:
            owner_id = getattr(obj, "user_id", None)
        return owner_id == request.user.id or request.user.is_staff


class IsForumModeratorOrAuthor(permissions.BasePermission):
    """Object author, forum moderators or staff may edit/delete forum content.

    Used for topics/replies/game comments: anyone authenticated may read,
    but writes are limited to the author of the object, holders of the
    ``community.can_moderate_forum`` permission, or staff.
    """

    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated)

    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True
        return (
            obj.author_id == request.user.id
            or request.user.has_perm("community.can_moderate_forum")
            or request.user.is_staff
        )


class IsForumModerator(permissions.BasePermission):
    """Forum moderators or staff only — used for moderation actions."""

    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and (request.user.has_perm("community.can_moderate_forum") or request.user.is_staff)
        )


class IsGamesModerator(permissions.BasePermission):
    """Games moderators or staff only — used for moderation actions."""

    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and (request.user.has_perm("catalog.can_moderate_games") or request.user.is_staff)
        )


class IsGamesModeratorOrReadOnly(permissions.BasePermission):
    """Any authenticated user can read; only games moderators/staff can write.

    Used for the catalogue (games/genres): regular users are read-only,
    holders of ``catalog.can_moderate_games`` (or staff) may write.
    """

    def has_permission(self, request, view):
        if not (request.user and request.user.is_authenticated):
            return False
        if request.method in permissions.SAFE_METHODS:
            return True
        return request.user.has_perm("catalog.can_moderate_games") or request.user.is_staff
