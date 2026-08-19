from dotenv import load_dotenv
from flask import Flask

from app.config import Config


def create_app(config_object: type = Config) -> Flask:
    load_dotenv()
    app = Flask(__name__)
    app.config.from_object(config_object)
    return app
