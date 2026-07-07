"""Page (shell) views. Each renders a static HTML template that then fetches
its data from the JSON endpoints in ``api.py``. All pages require login."""

from django.contrib.auth.decorators import login_required
from django.shortcuts import render


@login_required
def home(request):
    return render(request, "web/home.html", {"active": "home"})


@login_required
def bugometro(request):
    return render(request, "web/bugometro.html", {"active": "bugometro"})


@login_required
def community(request):
    return render(request, "web/community.html", {"active": "community"})


@login_required
def alerts(request):
    return render(request, "web/alerts.html", {"active": "alerts"})


@login_required
def game_detail(request, slug):
    return render(request, "web/game_detail.html", {"active": "home", "slug": slug})


@login_required
def profile(request):
    return render(request, "web/profile.html", {"active": "profile"})
