"""Entrypoint WSGI da aplicação Flask.

Usado a partir da fatia 7 por:
    gunicorn wsgi:app --bind 0.0.0.0:8000 --workers 3
    celery -A wsgi.celery worker -l info

Até lá o container ainda sobe o Django; este módulo existe para que a fatia 7
seja só uma troca de comando, sem código novo.
"""

from app import create_app

app = create_app()
celery = app.extensions["celery"]
