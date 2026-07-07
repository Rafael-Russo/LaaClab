"""Page (shell) view for the community domain (Comunidade).

Renders a static HTML template that then fetches its data from the JSON
endpoint in ``community/api.py``. Requires login.
"""

from django.contrib.auth.decorators import login_required
from django.shortcuts import render

from core.gating import require_module


@login_required
@require_module("community")
def community(request):
    return render(request, "web/community.html", {"active": "community"})
