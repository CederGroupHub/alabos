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


def parse_device_status(
    task_status: str,
    pause_status: str,
    attributes: dict[str, Any] | None = None,
) -> str:
    """Derive the dashboard-facing status string for a device.

    Permanently disabled devices (``attributes.disabled``) get their own status so the UI can
    distinguish them from operator-initiated pauses. A device that has not finished connecting
    reports ``CONNECTING``, which takes precedence over its pause status: alabos pauses such a
    device itself while it waits, and showing that as a plain ``PAUSED`` would look like an
    operator action and hide the fact that the device is simply not connected yet.
    """
    attributes = attributes or {}
    if attributes.get("disabled"):
        return "DISABLED"
    if attributes.get("connection_status") == "connecting":
        return "CONNECTING"
    if pause_status == "PAUSED":
        return "PAUSED"
    if pause_status == "REQUESTED":
        return "PAUSE_REQUESTED"
    return task_status


def published_attributes(device: dict[str, Any]) -> dict[str, Any]:
    """The subset of a device's stored attributes that it has opted into publishing.

    A device declares this with ``dashboard_attributes``. Anything not named there stays private,
    since attributes are also used for bulky internal bookkeeping that would bloat every poll of
    this endpoint.

    ``disabled`` and the connection bookkeeping written by ``DeviceView`` are always included, so
    every dashboard client can tell permanently disabled devices apart from operator pauses, and
    can explain a device that is not connected, without extra API calls.
    """
    allowed = device.get("dashboard_attributes") or []
    attributes = device.get("attributes") or {}
    published = {name: attributes.get(name) for name in allowed if name in attributes}
    published["disabled"] = bool(attributes.get("disabled"))
    disabled_reason = attributes.get("disabled_reason")
    if disabled_reason is not None:
        published["disabled_reason"] = disabled_reason
    published["connection_status"] = attributes.get("connection_status") or "connected"
    for name in (
        "connection_error",
        "connection_waiting_seconds",
        "connection_blocked_on_user_input",
        "connection_user_input_prompt",
    ):
        if attributes.get(name) is not None:
            published[name] = attributes[name]
    return published


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
            "status": parse_device_status(
                device["status"],
                device["pause_status"],
                device.get("attributes"),
            ),
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
