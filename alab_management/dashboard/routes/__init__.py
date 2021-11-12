from .experiment import experiment_bp
from .basic_route import modules


def init_app(app):
    app.register_blueprint(modules)
    app.register_blueprint(experiment_bp)
