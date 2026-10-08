"""The UI and API module."""

from __future__ import annotations

import logging
from pathlib import Path

from flask import Flask
from flask_cors import CORS  # type: ignore

from .routes import init_app as init_app_route

logger = logging.getLogger(__name__)


def _register_lab_extensions(app: Flask) -> None:
    """Mount optional lab-package routes (e.g. alab_one Submissions) when installed.

    Core AlabOS must start without any lab package. Lab-specific HTTP surfaces register
    themselves here so other labs are not forced to import ``alab_one``.
    """
    try:
        from alab_one.dashboard.alabos_extensions import register as register_alab_one
    except ImportError:
        logger.debug("No alab_one dashboard extensions (lab package not installed)")
        return
    try:
        register_alab_one(app)
    except Exception:
        logger.exception("Failed to register alab_one dashboard extensions")


def create_app(cors=False):
    """Create app, which is a factory function to be called when serving the app."""
    app = Flask(__name__, static_folder=(Path(__file__).parent / "ui").as_posix())
    if cors:
        CORS(app)
    init_app_route(app)
    _register_lab_extensions(app)
    return app
