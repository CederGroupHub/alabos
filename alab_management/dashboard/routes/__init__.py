from .experiment import experiment_bp


def init_app(app):
    app.register_blueprint(experiment_bp)
