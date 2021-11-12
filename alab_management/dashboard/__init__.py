from flask import Flask
from . import routes


def create_app():
    app = Flask(__name__)
    routes.init_app(app)
    return app
