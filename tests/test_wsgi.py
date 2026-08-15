def test_wsgi_expoe_app_e_celery(monkeypatch):
    """Os nomes que o gunicorn e o worker vão importar na fatia 7."""
    monkeypatch.setenv("APP_CONFIG", "test")
    import importlib

    import wsgi

    importlib.reload(wsgi)
    assert wsgi.app is not None
    assert wsgi.celery is not None
    assert wsgi.app.config["TESTING"] is True
