"""This is a dashboard that displays data from the ALab database."""

import logging
from datetime import datetime, timedelta
from bson import ObjectId  # type: ignore
from bson.errors import InvalidId  # type: ignore
from flask import Blueprint, request
from pydantic import ValidationError

from alab_management.dashboard.lab_views import experiment_view, sample_view, task_view
from alab_management.experiment_view.experiment import InputExperiment
from alab_management.experiment_view.experiment_view import ExperimentStatus
from alab_management.task_view.task_enums import TaskStatus
from alab_management.utils.data_objects import make_jsonable

logger = logging.getLogger(__name__)

experiment_bp = Blueprint("/experiment", __name__, url_prefix="/api/experiment")


@experiment_bp.route("/submit", methods=["POST"])
def submit_new_experiment():
    """Submit a new experiment to the system."""
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
    """Get the progress of an experiment."""
    try:
        experiment = experiment_view.get_experiment(ObjectId(exp_id))
    except ValueError as exception:
        return {"status": "error", "errors": exception.args[0]}

    if experiment is None:
        return {"status": "error", "errors": "Cannot find experiment with this exp id"}

    completed_task_count = 0
    error = False
    for task in experiment["tasks"]:
        task_status = task_view.get_status(task_id=task["task_id"])
        if task_status in [
            TaskStatus.COMPLETED,
            TaskStatus.ERROR,
            TaskStatus.CANCELLED,
        ]:
            completed_task_count += 1
        if task_status == TaskStatus.ERROR:
            error = True

    return completed_task_count / len(experiment["tasks"]), error


@experiment_bp.route("/get_all_ids", methods=["GET"])
def get_overview():
    """Get id for all experiments that are running or completed."""
    experiment_ids = []
    for status in [ExperimentStatus.RUNNING, ExperimentStatus.COMPLETED]:
        experiments = experiment_view.get_experiments_with_status(status)
        experiment_ids.extend(
            [
                str(exp["_id"])
                for exp in experiments
                if datetime.now() - exp.get("completed_at", datetime.now())
                <= timedelta(days=1)
            ]
        )

    return {"status": "success", "experiment_ids": experiment_ids}


@experiment_bp.route("/<exp_id>", methods=["GET"])
def query_experiment(exp_id: str):
    """Find an experiment by id. This is used by the dashboard to present experiment status."""
    try:
        experiment = experiment_view.get_experiment(ObjectId(exp_id))
    except InvalidId as exception:
        return {"status": "error", "errors": exception.args[0]}
    if experiment is None:
        return {"status": "error", "errors": "Cannot find experiment with this exp id"}

    progress, error_state = get_experiment_progress(exp_id)

    return_dict = {
        "id": str(experiment["_id"]),
        "name": experiment["name"],
        "submitted_at": experiment["submitted_at"],
        "samples": [
            {
                "name": sample["name"],
                "id": str(sample["sample_id"]),
                # Fall back to the last known location so the position field is never empty, even
                # after a sample leaves a position or an error occurs mid-transfer.
                "position": (
                    _sample_obj.position
                    if _sample_obj.position is not None
                    else _sample_obj.last_position
                ),
                "last_position": _sample_obj.last_position,
            }
            for sample in experiment["samples"]
            for _sample_obj in [sample_view.get_sample(sample["sample_id"])]
        ],
        "tasks": [],
        "progress": progress,
        "status": (
            experiment["status"] if not error_state else ExperimentStatus.ERROR.name
        ),
    }

    for task in experiment["tasks"]:
        task_entry = task_view.get_task(task["task_id"])
        return_dict["tasks"].append(
            {
                "id": str(task["task_id"]),
                "status": task_entry["status"],
                "type": task["type"],
                "message": task_entry.get("message", ""),
            }
        )
    return return_dict


@experiment_bp.route("/results/<exp_id>", methods=["GET"])
def query_experiment_results(exp_id: str):
    """Find an experiment by id. This is intended for users to retrieve data from an experiment."""
    try:
        experiment = experiment_view.get_experiment(ObjectId(exp_id))
    except InvalidId as exception:
        return {"status": "error", "errors": exception.args[0]}
    if experiment is None:
        return {"status": "error", "errors": "Cannot find experiment with this exp id"}

    progress, _error_state = get_experiment_progress(exp_id)

    return_dict = {
        "id": str(experiment["_id"]),
        "name": experiment["name"],
        "tags": experiment.get("tags", []),
        "metadata": experiment.get("metadata", {}),
        "samples": [],
        "tasks": [],
        "status": experiment["status"],
        "submitted_at": experiment["submitted_at"],
        "progress": progress,
        "completed_at": experiment.get("completed_at", None),
    }

    for sample in experiment["samples"]:
        return_dict["samples"].append(
            {
                "name": sample["name"],
                "metadata": sample.get("metadata", {}),
                "tags": sample.get("tags", []),
                "id": str(sample["sample_id"]),
            }
        )

    for task in experiment["tasks"]:
        task_entry = task_view.get_task(task["task_id"])
        return_dict["tasks"].append(
            {
                "type": task["type"],
                "parameters": task["parameters"],
                "message": task_entry.get("message", ""),
                "result": task_entry.get("result", {}),
                "id": str(task["task_id"]),
                "status": task_entry["status"],
                "started_at": task_entry.get("started_at", None),
                "completed_at": task_entry.get("completed_at", None),
                "samples": [sample["name"] for sample in task_entry["samples"]],
                # "subtasks": task_entry.get("subtasks", []),
            }
        )

    return make_jsonable(return_dict)


@experiment_bp.route("/cancel/<exp_id>", methods=["GET"])
def cancel_experiment(exp_id: str):
    """Cancel one experiment and free only that experiment's software bookings."""
    from alab_management.experiment_cancel import cancel_experiment_software_state

    try:
        summary = cancel_experiment_software_state(ObjectId(exp_id))
    except InvalidId as exception:
        return {"status": "error", "reason": exception.args[0]}, 400
    except ValueError as exception:
        return {"status": "error", "reason": str(exception)}, 400
    except Exception as exception:
        logger.exception("Cancel experiment failed")
        return {"status": "error", "reason": str(exception)}, 500
    return {"status": "success", "data": summary}


@experiment_bp.route("/reset_lab", methods=["POST"])
def reset_lab():
    """Cancel every live experiment and release the lab's software state."""
    from alab_management.lab_reset import reset_lab_software_state

    try:
        summary = reset_lab_software_state()
    except Exception as exception:
        logger.exception("Reset lab failed")
        return {"status": "error", "reason": str(exception)}, 500
    return {"status": "success", "data": summary}
