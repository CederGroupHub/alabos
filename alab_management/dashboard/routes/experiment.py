from bson import ObjectId
from bson.errors import InvalidId
from flask import Blueprint, request
from pydantic import ValidationError

from alab_management.experiment_view.experiment import InputExperiment
from alab_management.experiment_view.experiment_view import ExperimentStatus
from alab_management.task_view.task_enums import TaskStatus
from ..lab_views import experiment_view, sample_view, task_view

experiment_bp = Blueprint("/experiment", __name__, url_prefix="/api/experiment")


@experiment_bp.route("/submit", methods=["POST"])
def submit_new_experiment():
    """
    Submit a new experiment to the system
    """
    data = request.get_json(force=True)  # type: ignore
    try:
        experiment = InputExperiment(**data)  # type: ignore
        exp_id = experiment_view.create_experiment(experiment)
    except ValidationError as exception:
        return {"status": "error", "errors": exception.errors()}, 400
    except ValueError as exception:
        return {"status": "error", "errors": exception.args[0]}, 400

    return {"status": "success", "data": {"exp_id": str(exp_id)}}


def get_experiment_progress(exp_id: str):
    """
    Get the progress of an experiment
    """
    try:
        experiment = experiment_view.get_experiment(ObjectId(exp_id))
    except ValueError as exception:
        return {"status": "error", "errors": exception.args[0]}

    completed_task_count = 0
    error = False
    for task in experiment["tasks"]:
        task_status = task_view.get_status(task_id=task["task_id"])
        if task_status == TaskStatus.COMPLETED:
            completed_task_count += 1
        if task_status == TaskStatus.ERROR:
            error = True

    return completed_task_count / len(experiment["tasks"]), error


@experiment_bp.route("/get_all_ids", methods=["GET"])
def get_overview():
    """
    get id for all experiments that are running or completed
    """
    experiment_ids = []
    for status in [ExperimentStatus.RUNNING, ExperimentStatus.COMPLETED]:
        experiments = experiment_view.get_experiments_with_status(status)
        experiment_ids.extend([str(exp["_id"]) for exp in experiments])

    return {"status": "success", "experiment_ids": experiment_ids}


@experiment_bp.route("/<exp_id>", methods=["GET"])
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

    progress, error_state = get_experiment_progress(exp_id)
    return {
        "id": str(experiment["_id"]),
        "name": experiment["name"],
        "submitted_at": experiment["submitted_at"],
        "samples": [
            {
                "name": sample["name"],
                "id": str(sample["sample_id"]),
                "position": sample_view.get_sample(sample["sample_id"]).position,
            }
            for sample in experiment["samples"]
        ],
        "tasks": [
            {
                "id": str(task["task_id"]),
                "status": task_view.get_status(task["task_id"]).name,
                "type": task["type"],
                "message": task_view.get_task(task["task_id"]).get("message", ""),
                "result": task_view.get_task(task["task_id"]).get("result", ""),
            }
            for task in experiment["tasks"]
        ],
        "progress": progress,
        "status": experiment["status"]
        if not error_state
        else ExperimentStatus.ERROR.value,
    }
