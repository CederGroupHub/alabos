from flask import Flask
from . import routes


def create_app():
    """
    Create app, which is a factory function to be called when serving the app
    """
    app = Flask(__name__)
    routes.init_app(app)
    return app
