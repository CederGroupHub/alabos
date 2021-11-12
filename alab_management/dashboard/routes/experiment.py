from bson import ObjectId
from bson.errors import InvalidId
from flask import Blueprint, request
from pydantic import ValidationError

from alab_management.experiment_view.experiment import InputExperiment
from ..lab_views import experiment_view

experiment_bp = Blueprint("/experiment", __name__, url_prefix="/experiment")


@experiment_bp.route("/submit", methods=["POST"])
def submit_new_experiment():
    """
    Submit a new experiment to the system
    """
    data = request.get_json(force=True)
    try:
        experiment = InputExperiment(**data)
    except ValidationError as exception:
        return {"status": "error", "errors": exception.errors()}, 400

    exp_id = experiment_view.create_experiment(experiment)
    return {"status": "success", "data": {"exp_id": str(exp_id)}}


@experiment_bp.route("/search/<exp_id>", methods=["POST", "GET"])
def query_experiment(exp_id: str):
    """
    Find an experiment by id
    """
    try:
        experiment = experiment_view.get_experiment(ObjectId(exp_id))
    except InvalidId as exception:
        return {"status": "error", "errors": exception.args[0]}
    if experiment is None:
        return {"status": "error", "errors": "Cannot find experiment with this exp id"}
    return {
        "id": experiment["_id"],
        "name": experiment["name"],
        "tasks": experiment["tasks"],
        "samples": experiment["samples"],
        "status": experiment["status"],
    }
