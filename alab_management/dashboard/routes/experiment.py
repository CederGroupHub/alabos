"""This is a dashboard that displays data from the ALab database."""

import logging
from datetime import datetime, timedelta
from bson import ObjectId  # type: ignore
from bson.errors import InvalidId  # type: ignore
from flask import Blueprint, request
from pydantic import ValidationError

from alab_management.dashboard.experiment_progress import (
    compute_progress_steps,
    summarize_task,
)
from alab_management.dashboard.lab_views import experiment_view, sample_view, task_view
from alab_management.experiment_view.experiment import InputExperiment
from alab_management.experiment_view.experiment_view import (
    ExperimentStatus,
    dashboard_experiment_status,
)
from alab_management.task_view.task_enums import TaskStatus
from alab_management.utils.data_objects import make_jsonable

logger = logging.getLogger(__name__)

experiment_bp = Blueprint("/experiment", __name__, url_prefix="/api/experiment")


@experiment_bp.route("/submit", methods=["POST"])
def submit_new_experiment():
    """Submit a new experiment to the system."""
    from alab_management.device_rpc_status import (
        ensure_lab_starting_user_input,
        get_lab_readiness,
    )

    data = request.get_json(force=True)  # type: ignore
    try:
        experiment = InputExperiment(**data)  # type: ignore
        exp_id = experiment_view.create_experiment(experiment)
    except ValidationError as exception:
        return {"status": "error", "errors": exception.errors()}, 400
    except ValueError as exception:
        return {"status": "error", "errors": exception.args[0]}, 400

    readiness = get_lab_readiness()
    held = not readiness["lab_ready"]
    if held:
        ensure_lab_starting_user_input()

    return {
        "status": "success",
        "data": {
            "exp_id": str(exp_id),
            "lab_ready": readiness["lab_ready"],
            "lab_ready_label": readiness["lab_ready_label"],
            "held_until_lab_ready": held,
        },
    }


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
    for status in [
        ExperimentStatus.RUNNING,
        ExperimentStatus.COMPLETED,
        ExperimentStatus.CANCELLED,
        ExperimentStatus.ERROR,
    ]:
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

    progress, _error_state = get_experiment_progress(exp_id)

    return_dict = {
        "id": str(experiment["_id"]),
        "name": experiment["name"],
        "submitted_at": experiment["submitted_at"],
        "samples": [
            _sample_payload_for_experiment(sample) for sample in experiment["samples"]
        ],
        "tasks": [],
        "progress": progress,
        "status": experiment["status"],
        "progress_steps": {"previous": [], "current": [], "next": []},
    }

    task_docs = []
    for task in experiment["tasks"]:
        task_entry = task_view.get_task(task["task_id"])
        # Prefer experiment graph type when present; keep Mongo fields for status/edges.
        merged = dict(task_entry)
        merged.setdefault("type", task.get("type"))
        if task.get("type"):
            merged["type"] = task["type"]
        task_docs.append(merged)
        summary = summarize_task(merged)
        return_dict["tasks"].append(summary)

    return_dict["progress_steps"] = compute_progress_steps(task_docs)
    return_dict["status"] = dashboard_experiment_status(
        [task["status"] for task in return_dict["tasks"]],
        experiment["status"],
    )
    return make_jsonable(return_dict)


def _sample_payload_for_experiment(sample: dict) -> dict:
    """Build the dashboard sample row; tolerate samples pruned from live into completed.

    Cancel / Clear occupancy may archive then prune live sample docs while the live
    experiment row still references them. Looking those up must not 500 the Experiments
    page every poll.
    """
    sample_id = sample.get("sample_id")
    name = sample.get("name")
    position = None
    last_position = None

    if sample_id is not None:
        try:
            live = sample_view.get_sample(sample_id)
        except ValueError:
            live = None
        if live is not None:
            position = live.position
            last_position = live.last_position
            name = live.name or name
        else:
            archived = _completed_sample_doc(sample_id)
            if archived is not None:
                position = archived.get("position")
                last_position = archived.get("last_position")
                name = archived.get("name") or name

    display_position = position if position is not None else last_position
    return {
        "name": name,
        "id": str(sample_id) if sample_id is not None else None,
        "position": display_position,
        "last_position": last_position,
    }


def _completed_sample_doc(sample_id: ObjectId) -> dict | None:
    """Return the archived sample document when ``mongodb_completed`` is configured."""
    try:
        from alab_management.config import AlabOSConfig
        from alab_management.utils.data_objects import get_completed_collection

        if "mongodb_completed" not in AlabOSConfig():
            return None
        return get_completed_collection("samples").find_one({"_id": sample_id})
    except Exception:  # noqa: BLE001 — dashboard must stay up if completed is down
        logger.debug(
            "Could not load sample %s from completed database", sample_id, exc_info=True
        )
        return None


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
        logger.exception("Release locks & tasks failed")
        return {"status": "error", "reason": str(exception)}, 500
    return {"status": "success", "data": summary}
