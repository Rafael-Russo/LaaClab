from flask import Flask

from app.config import Config


def create_app(config_object: type = Config) -> Flask:
    app = Flask(__name__)
    app.config.from_object(config_object)

    from app.extensions import csrf, login_manager

    csrf.init_app(app)
    login_manager.init_app(app)

    from app.telas import bp as telas_bp

    app.register_blueprint(telas_bp)

    from app.auth import bp as auth_bp

    app.register_blueprint(auth_bp)

    return app
