"""App factory do LaaCLab."""

from flask import Flask, jsonify, request
from werkzeug.exceptions import HTTPException
from whitenoise import WhiteNoise

from app.celery_app import celery_init_app
from app.config import BaseConfig, get_config
from app.extensions import api, csrf, db, login_manager, mail, migrate
from app.security import register_host_check, register_https_enforcement, register_proxy_fix


def create_app(config: BaseConfig | None = None) -> Flask:
    app = Flask(__name__, static_folder="static", template_folder="templates")
    app.config.from_object(config or get_config())

    # A checagem de Host precisa rodar antes do CSRFProtect (registrado dentro
    # de _register_extensions): o Flask-WTF monta o referrer esperado a partir
    # de request.host no próprio before_request, e se o CSRF rodar primeiro
    # ele usa um Host que a allowlist ainda não validou.
    register_host_check(app)
    register_https_enforcement(app)

    _register_extensions(app)
    _register_error_handlers(app)
    celery_init_app(app)
    _register_blueprints(app)
    _register_context_processors(app)

    @app.get("/healthz")
    def healthz():
        """Liveness probe simples; ainda não referenciada pelo compose nem pelo nginx."""
        return jsonify({"status": "ok"})

    register_proxy_fix(app)
    _register_static(app)

    from app.core.cli import register_cli

    register_cli(app)

    return app


def _register_extensions(app: Flask) -> None:
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    login_manager.login_view = "accounts.login"
    login_manager.login_message = "Faça login para continuar."
    login_manager.login_message_category = "info"
    csrf.init_app(app)
    mail.init_app(app)
    # Monta /api/v1/openapi.json e o Swagger UI em /api/v1/docs. Fica vazio
    # até a fatia 1 registrar o primeiro recurso.
    api.init_app(app)


def _register_error_handlers(app: Flask) -> None:
    """Reparte o tratamento de erro entre API e páginas.

    `api.init_app` (chamado em `_register_extensions`, logo antes desta
    função) registra por conta própria um handler de `HTTPException` na
    aplicação inteira — `Flask.register_error_handler` guarda os handlers em
    `error_handler_spec[None][None][HTTPException]`, uma única entrada por
    app, então um segundo `app.errorhandler(HTTPException)` não convive com o
    do smorest: ele *substitui* a entrada, e a partir daqui só o nosso roda
    para qualquer `HTTPException` levantada em qualquer rota, API ou não.

    Por isso este handler decide sozinho, por prefixo de caminho, o que
    fazer: em `/api/v1/...` delega para `api.handle_http_exception` — o
    método do próprio objeto `Api` já inicializado, chamado direto (não há
    outra forma pública de alcançar o handler do smorest depois do
    `init_app`) — que devolve exatamente o mesmo JSON que a API sempre
    devolveu. Fora da API, devolve a exceção como está: é o mesmo fallback
    que `Flask.handle_http_exception` usaria se não houvesse handler nenhum
    registrado, então a página de erro HTML padrão do Werkzeug volta a
    aparecer — e com ela a `description` passada a `abort()`, que o handler
    do smorest descartava silenciosamente.
    """
    prefixo_api = app.config["OPENAPI_URL_PREFIX"]

    @app.errorhandler(HTTPException)
    def _tratar_erro(erro: HTTPException):
        if request.path.startswith(prefixo_api):
            return api.handle_http_exception(erro)
        return erro


def _register_blueprints(app: Flask) -> None:
    from app.accounts.rest import bp as me_bp
    from app.accounts.views import bp as accounts_bp
    from app.core import bp as core_bp

    app.register_blueprint(accounts_bp)
    app.register_blueprint(core_bp)
    api.register_blueprint(me_bp)


def _register_context_processors(app: Flask) -> None:
    """Expõe `visible_modules` a todo template.

    O Jinja2 até chamaria uma função com argumento, mas manter um conjunto
    preserva a forma que os templates já usam: `{% if 'community' in
    visible_modules %}`.
    """

    @app.context_processor
    def _modulos():
        from app.core.models import MODULE_CANDIDATES, Module

        desligados = {
            m.key for m in db.session.query(Module).filter_by(enabled=False).all()
        }
        return {"visible_modules": MODULE_CANDIDATES - desligados}


def _register_static(app: Flask) -> None:
    """Fora de debug, o WhiteNoise serve /static/ direto do WSGI.

    É middleware WSGI puro — independe de framework, e por isso sobrevive à
    saída do Django. Em debug o Flask serve sozinho, com recarga imediata.
    """
    if app.debug or app.testing:
        return
    app.wsgi_app = WhiteNoise(
        app.wsgi_app,
        root=str(app.static_folder),
        prefix=app.static_url_path.lstrip("/") + "/",
        autorefresh=False,
    )
