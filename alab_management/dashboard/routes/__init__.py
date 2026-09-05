"""This is a dashboard that displays data from the ALab database."""

from .basic_route import modules
from .bft_control import bft_control_bp
from .dash_control import dash_control_bp
from .data import data_bp
from .device import device_bp
from .device_control import device_control_bp
from .experiment import experiment_bp
from .pause import pause_bp
from .robot_control import robot_control_bp
from .sample_positions import sample_positions_bp
from .status import status_bp
from .task import task_bp
from .user_input import userinput_bp


def init_app(app):
    """Add routes to the app."""
    app.register_blueprint(modules)
    app.register_blueprint(bft_control_bp)
    app.register_blueprint(dash_control_bp)
    app.register_blueprint(data_bp)
    app.register_blueprint(device_bp)
    app.register_blueprint(device_control_bp)
    app.register_blueprint(experiment_bp)
    app.register_blueprint(sample_positions_bp)
    app.register_blueprint(status_bp)
    app.register_blueprint(userinput_bp)
    app.register_blueprint(pause_bp)
    app.register_blueprint(robot_control_bp)
    app.register_blueprint(task_bp)
