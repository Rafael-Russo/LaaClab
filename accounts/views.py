"""Page (shell) view for the accounts domain (Perfil).

Renders a static HTML template that then fetches its data from the JSON
endpoints in ``accounts/api.py``. Requires login.
"""

from django.contrib.auth.decorators import login_required
from django.shortcuts import render


@login_required
def profile(request):
    return render(request, "web/profile.html", {"active": "profile"})
