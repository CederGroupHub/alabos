from flask import Blueprint

modules = Blueprint("basic_route", __name__)


@modules.route("/")
def index():
    return "This is the Alab OS dashboard."
