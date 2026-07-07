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

    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True
        owner_id = getattr(obj, "author_id", None)
        if owner_id is None:
            owner_id = getattr(obj, "user_id", None)
        return owner_id == request.user.id or request.user.is_staff
