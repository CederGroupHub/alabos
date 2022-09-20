from flask import Blueprint

from ..lab_views import (
    device_view,
    experiment_view,
    task_view,
    user_input_view,
    sample_view,
)

status_bp = Blueprint("/status", __name__, url_prefix="/api/status")


def parse_device_status(task_status: str, pause_status: str) -> str:
    if pause_status == "PAUSED":
        return "PAUSED"
    elif pause_status == "REQUESTED":
        return "PAUSE_REQUESTED"
    else:
        return task_status


@status_bp.route("/")
def get_all_status():
    """
    Get all the status in the database
    """
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
            "samples": {
                position: [
                    {
                        "id": str(sample_id),
                        "name": sample_view.get_sample(sample_id).name,
                    }
                    for sample_id in samples
                ]
                for position, samples in device_view.get_samples_on_device(
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

    return {
        "devices": devices,
        "experiments": experiments,
        # "userinputrequests": user_input_requests,
    }
