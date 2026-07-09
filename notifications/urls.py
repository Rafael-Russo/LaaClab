"""URL routes for the notifications per-screen JSON endpoints consumed by
the topbar bell (list, mark-one-read, mark-all-read).
"""

from django.urls import path

from . import api

urlpatterns = [
    path("api/notifications/", api.notifications, name="api_notifications"),
    path("api/notifications/read-all/", api.mark_all_read, name="api_notifications_read_all"),
    path("api/notifications/<int:pk>/read/", api.mark_read, name="api_notification_read"),
]
