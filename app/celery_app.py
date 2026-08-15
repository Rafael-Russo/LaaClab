"""Integração Celery ↔ Flask.

A `Task` base abre um app context antes de rodar, de modo que as tasks possam
usar `db.session`, `current_app.config` e os services exatamente como as views.
Substitui o `config/celery.py` do Django, que ganhava isso do `django.setup()`.
"""

from celery import Celery, Task
from flask import Flask


def celery_init_app(app: Flask) -> Celery:
    class FlaskTask(Task):
        def __call__(self, *args, **kwargs):
            with app.app_context():
                return self.run(*args, **kwargs)

    celery_app = Celery(app.name, task_cls=FlaskTask)
    celery_app.conf.update(app.config["CELERY"])
    # set_default faz o `shared_task` dos módulos de domínio resolver para
    # esta instância sem precisar importá-la. Atenção: isto muta estado
    # process-global (`celery._state.default_app`) — sobrevive à app que o
    # criou. Testes que criam mais de uma app precisam restaurar isso (ver
    # `_celery_default_restaurado` em tests/conftest.py).
    celery_app.set_default()
    app.extensions["celery"] = celery_app
    return celery_app
