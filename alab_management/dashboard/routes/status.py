from flask import Blueprint

from ..lab_views import device_view, experiment_view, task_view

status_bp = Blueprint("/status", __name__, url_prefix="/api/status")


@status_bp.route("/")
def get_all_status():
    """
    Get all the status in the database
    """
    devices = device_view.get_all()
    experiments = experiment_view.get_experiments_with_status("RUNNING")
    experiments = [{
        "id": str(experiment["_id"]),
        "name": experiment["name"],
        "samples": [{"name": sample["name"], "id": str(sample["sample_id"])}
                    for sample in experiment["samples"]],
        "tasks": [{"id": str(task["task_id"]), "status": task_view.get_status(task["task_id"]).name,
                   "type": task["type"]}
                  for task in experiment["tasks"]]
    } for experiment in experiments]
    return {
        "devices": [{
            "name": device["name"],
            "type": device["type"],
            "status": device["status"],
            "task": str(device["task_id"]) if device["task_id"] is not None else "null",
        } for device in devices],
        "experiments": experiments,
    }
