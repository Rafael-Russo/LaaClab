"""Per-screen JSON endpoints for the accounts domain (perfil + me), consumed
by the sidebar widget, top bar and profile screen via ``fetch()``.
"""

from django.http import JsonResponse

from core.api import api_login_required

from .models import UserProfile


def _user_payload(user) -> dict:
    """Profile summary for the sidebar widget, top bar and profile screen."""
    profile, _ = UserProfile.objects.get_or_create(user=user)
    return {
        "username": user.username,
        "handle": profile.handle or user.username,
        "level": profile.level,
        "xp": profile.xp,
        "xp_max": profile.xp_max,
        "bio": profile.bio,
        "achievements": profile.achievements,
        "friends": profile.friends,
        "days_active": profile.days_active,
        "avatar_color": profile.avatar_color,
    }


@api_login_required
def me(request):
    return JsonResponse(_user_payload(request.user))


@api_login_required
def profile(request):
    entries = (
        request.user.library.select_related("game").order_by("-added_at")[:3]
    )
    recent = [
        {
            "game": e.game.name,
            "duration": f"{e.game.bug_score // 3}h {e.game.bug_score % 60:02d}m",
            "percent": e.game.bug_score,
            "cover": e.game.cover or ["#2b2d47", "#14352b"],
        }
        for e in entries
    ]
    return JsonResponse({"user": _user_payload(request.user), "recent_games": recent})
