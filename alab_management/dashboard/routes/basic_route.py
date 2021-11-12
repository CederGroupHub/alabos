from flask import Blueprint

modules = Blueprint("basic_route", __name__)


@modules.route("/")
def index():
    """
    Index page of the dashboard
    """
    return "This is the Alab OS dashboard."
