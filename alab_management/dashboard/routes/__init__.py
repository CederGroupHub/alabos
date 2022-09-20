from .basic_route import modules
from .experiment import experiment_bp
from .status import status_bp
from .user_input import userinput_bp
from .pause import pause_bp


def init_app(app):
    """
    Add routes to the app
    """
    app.register_blueprint(modules)
    app.register_blueprint(experiment_bp)
    app.register_blueprint(status_bp)
    app.register_blueprint(userinput_bp)
    app.register_blueprint(pause_bp)
