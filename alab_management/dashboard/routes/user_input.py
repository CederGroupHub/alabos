from bson import ObjectId  # type: ignore
from flask import Blueprint, request

from alab_management.dashboard.lab_views import (
    experiment_view,
    task_view,
    user_input_view,
)
from alab_management.utils.data_objects import get_completed_collection

userinput_bp = Blueprint("/userinput", __name__, url_prefix="/api/userinput")


def _batch_fetch_tasks(task_ids: set[ObjectId]) -> dict[ObjectId, dict]:
    if not task_ids:
        return {}

    tasks_by_id: dict[ObjectId, dict] = {}
    for task in task_view._task_collection.find({"_id": {"$in": list(task_ids)}}):
        tasks_by_id[task["_id"]] = task

    missing = task_ids - set(tasks_by_id)
    if missing:
        try:
            completed_tasks = get_completed_collection("tasks")
            for task in completed_tasks.find({"_id": {"$in": list(missing)}}):
                tasks_by_id[task["_id"]] = task
        except ValueError:
            pass

    return tasks_by_id


def _batch_fetch_experiments(experiment_ids: set[ObjectId]) -> dict[ObjectId, dict]:
    if not experiment_ids:
        return {}

    experiments_by_id: dict[ObjectId, dict] = {}
    for experiment in experiment_view._experiment_collection.find(
        {"_id": {"$in": list(experiment_ids)}}
    ):
        experiments_by_id[experiment["_id"]] = experiment

    missing = experiment_ids - set(experiments_by_id)
    if missing:
        try:
            completed_experiments = get_completed_collection("experiment")
            for experiment in completed_experiments.find(
                {"_id": {"$in": list(missing)}}
            ):
                experiments_by_id[experiment["_id"]] = experiment
        except ValueError:
            pass

    return experiments_by_id


@userinput_bp.route("/pending", methods=["GET"])
def get_userinput_status():
    """Get all the status in the database."""
    pending_requests = list(user_input_view.get_all_pending_requests())

    task_ids: set[ObjectId] = set()
    experiment_ids: set[ObjectId] = set()
    for request_ in pending_requests:
        context = request_["request_context"]
        if "task_id" in context:
            task_ids.add(ObjectId(context["task_id"]))
        if not context.get("maintenance") and "experiment_id" in context:
            experiment_ids.add(ObjectId(context["experiment_id"]))

    tasks_by_id = _batch_fetch_tasks(task_ids)
    experiments_by_id = _batch_fetch_experiments(experiment_ids)

    user_input_requests = {}
    id_to_name = {}
    for request_ in pending_requests:
        context = request_["request_context"]
        if context.get("maintenance"):
            experiment_name = "Maintenance"
            eid = "Maintenance"
            if "task_id" not in context:
                task_id = "This request came directly from a device, no task_id."
                task_type = "DeviceRequest"
            else:
                task_object_id = ObjectId(context["task_id"])
                task_id = str(task_object_id)
                task_doc = tasks_by_id.get(task_object_id)
                if task_doc is None:
                    raise ValueError(f"No task exists with provided task id: {task_object_id}")
                task_type = task_doc["type"]
        else:
            experiment_object_id = ObjectId(context["experiment_id"])
            eid = str(experiment_object_id)
            experiment_doc = experiments_by_id.get(experiment_object_id)
            if experiment_doc is None:
                raise ValueError(f"Cannot find an experiment with id: {experiment_object_id}")
            experiment_name = experiment_doc["name"]
            task_object_id = ObjectId(context["task_id"])
            task_id = str(task_object_id)
            task_doc = tasks_by_id.get(task_object_id)
            if task_doc is None:
                raise ValueError(f"No task exists with provided task id: {task_object_id}")
            task_type = task_doc["type"]

        if eid not in user_input_requests:
            user_input_requests[eid] = []
            id_to_name[eid] = experiment_name

        user_input_requests[eid].append(
            {
                "id": str(request_["_id"]),
                "prompt": request_["prompt"],
                "task": {
                    "id": task_id,
                    "type": task_type,
                },
                "options": request_["options"],
            }
        )
    return {
        "pending_requests": user_input_requests,
        "experiment_id_to_name": id_to_name,
    }


@userinput_bp.route("/submit", methods=["POST"])
def submit_user_input():
    """Update status of user input request."""
    data = request.get_json(force=True)  # type: ignore
    # return {"dummy": "dummy"}
    try:
        user_input_view.update_request_status(
            request_id=ObjectId(data["request_id"]),
            response=data["response"],
            note=data["note"],
        )
    except Exception as exception:
        return {"status": "error", "errors": exception.args[0]}, 400
    # except ValidationError as exception:
    #     return {"status": "error", "errors": exception.errors()}, 400
    # except ValueError as exception:
    #     return {"status": "error", "errors": exception.errors()}, 400

    return {"status": "success", "data": data}


@userinput_bp.route("/<request_id>", methods=["GET"])
def query_user_input(request_id: str):
    """Find an user input request by idresponse."""
    try:
        user_input_request = user_input_view.get_request(
            request_id=ObjectId(request_id)
        )
    except ValueError as exception:
        return {"status": "error", "errors": exception.args[0]}
    return {
        "id": str(user_input_request["_id"]),
        "prompt": user_input_request["prompt"],
        "task_id": str(user_input_request["task_id"]),
        "experiment_id": str(user_input_request["experiment_id"]),
        "options": user_input_request["options"],
        "status": user_input_request["status"],
    }
