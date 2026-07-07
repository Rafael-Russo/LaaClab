"""Page (shell) view for the alerts domain (Alertas).

Renders a static HTML template that then fetches its data from the JSON
endpoint in ``alerts/api.py``. Requires login.
"""

from django.contrib.auth.decorators import login_required
from django.shortcuts import render


@login_required
def alerts(request):
    return render(request, "web/alerts.html", {"active": "alerts"})
