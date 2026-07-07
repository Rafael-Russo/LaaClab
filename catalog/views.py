"""Page (shell) views for the catalogue domain (Explorar/Biblioteca).

Each renders a static HTML template that then fetches its data from the
JSON endpoint in ``catalog/api.py``. Both pages require login.
"""

from django.contrib.auth.decorators import login_required
from django.shortcuts import render

from core.gating import require_module


@login_required
@require_module("catalog")
def library(request):
    return render(request, "web/library.html", {"active": "library"})


@login_required
@require_module("catalog")
def explore(request):
    return render(request, "web/explore.html", {"active": "explore"})
