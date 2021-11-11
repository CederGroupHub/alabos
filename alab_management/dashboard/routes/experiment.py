from bson import ObjectId
from flask import Blueprint, request
from pydantic import ValidationError

from alab_management.experiment_view.experiment import InputExperiment
from ..models import experiment_view

experiment_bp = Blueprint("/experiment", __name__)


@experiment_bp.route("/submit", methods=["POST"])
def submit_new_experiment():
    data = request.get_json(force=True)
    try:
        experiment = InputExperiment(**data)
    except ValidationError as e:
        return {"status": "error", "errors": e.errors()}, 400

    exp_id = experiment_view.create_experiment(experiment)
    return {"status": "success", "data": {"exp_id": str(exp_id)}}


@experiment_bp.route("/<exp_id:exp_id>", methods=["POST", "GET"])
def query_experiment(exp_id: str):
    experiment = experiment_view.get_experiment(ObjectId(exp_id))
    if experiment is None:
        return None
    return {
        "id": experiment["_id"],
        "name": experiment["name"],
        "tasks": experiment["tasks"],
        "samples": experiment["samples"],
        "status": experiment["status"],
    }


@experiment_bp.route("/<exp_id:exp_id>/edit", methods=["POST"])
def edit_experiment(exp_id: str):
    experiment = experiment_view.get_experiment(ObjectId(exp_id))
    if experiment is None:
        return None
    data = request.get_json(force=True)
