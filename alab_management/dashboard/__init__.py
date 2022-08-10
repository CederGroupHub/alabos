"""
The UI and API module.
"""

from pathlib import Path

from flask import Flask
from flask_cors import CORS
from .routes import init_app as init_app_route


def create_app(cors=False):
    """
    Create app, which is a factory function to be called when serving the app
    """
    app = Flask(__name__, static_folder=(Path(__file__).parent / "ui").as_posix())
    if cors:
        CORS(app)
    init_app_route(app)
    return app
