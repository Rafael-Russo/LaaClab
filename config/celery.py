"""Celery application for LaaCLab.

Reads its config from Django settings (keys prefixed with ``CELERY_``) and
auto-discovers tasks in the installed apps (``catalog/tasks.py``).
"""

import os

from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

app = Celery("laaclab")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()
