from typing import Any

from flask import Blueprint

from alab_management.dashboard.lab_views import (
    device_view,
    experiment_view,
    sample_view,
    task_view,
)
from alab_management.utils.data_objects import make_jsonable

status_bp = Blueprint("/status", __name__, url_prefix="/api/status")


def parse_device_status(task_status: str, pause_status: str) -> str:
    if pause_status == "PAUSED":
        return "PAUSED"
    elif pause_status == "REQUESTED":
        return "PAUSE_REQUESTED"
    else:
        return task_status


def published_attributes(device: dict[str, Any]) -> dict[str, Any]:
    """The subset of a device's stored attributes that it has opted into publishing.

    A device declares this with ``dashboard_attributes``. Anything not named there stays private,
    since attributes are also used for bulky internal bookkeeping that would bloat every poll of
    this endpoint.
    """
    allowed = device.get("dashboard_attributes") or []
    attributes = device.get("attributes") or {}
    return {name: attributes.get(name) for name in allowed if name in attributes}


def describe_sample(sample_id) -> dict[str, Any]:
    """Name, id and, when it is being moved, where the sample is coming from and going to."""
    sample = sample_view.get_sample(sample_id)
    described: dict[str, Any] = {"id": str(sample_id), "name": sample.name}
    if sample.in_transit:
        described["in_transit"] = sample.in_transit
    return described


@status_bp.route("/")
def get_all_status():
    """Get all the status in the database."""
    devices = device_view.get_all()
    devices = [
        {
            "name": device["name"],
            "type": device["type"],
            "task_status": device["status"],
            "pause_status": device["pause_status"],
            "status": parse_device_status(device["status"], device["pause_status"]),
            "message": device["message"],
            "task": str(device["task_id"]) if device["task_id"] is not None else "null",
            "attributes": published_attributes(device),
            "samples": {
                position: [describe_sample(sample_id) for sample_id in samples]
                for position, samples in sample_view.get_samples_on_device(
                    device["name"]
                ).items()
            },
        }
        for device in devices
    ]

    # user_input_requests = user_input_view.get_all_pending_requests()
    # user_input_requests = [
    #     {
    #         "id": str(request["_id"]),
    #         "prompt": request["prompt"],
    #         "task_id": str(request["task_id"]),
    #     }
    #     for request in user_input_requests
    # ]

    experiments = experiment_view.get_experiments_with_status("RUNNING")
    experiments = [
        {
            "id": str(experiment["_id"]),
            "name": experiment["name"],
            "samples": [
                {"name": sample["name"], "id": str(sample["sample_id"])}
                for sample in experiment["samples"]
            ],
            "tasks": [
                {
                    "id": str(task["task_id"]),
                    "status": task_view.get_status(task["task_id"]).name,
                    "type": task["type"],
                }
                for task in experiment["tasks"]
            ],
        }
        for experiment in experiments
    ]

    return make_jsonable(
        {
            "devices": devices,
            "experiments": experiments,
            # "userinputrequests": user_input_requests,
        }
    )
