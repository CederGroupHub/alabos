from bson import ObjectId
from flask import Blueprint, request

from alab_management.dashboard.lab_views import (
    experiment_view,
    task_view,
    user_input_view,
)

userinput_bp = Blueprint("/userinput", __name__, url_prefix="/api/userinput")


@userinput_bp.route("/pending", methods=["GET"])
def get_userinput_status():
    """Get all the status in the database."""
    user_input_requests = {}
    id_to_name = {}
    for request in user_input_view.get_all_pending_requests():
        if request["request_context"]["maintenance"]:
            experiment_name = "Maintenance"
            eid = "Maintenance"
            if "task_id" not in request["request_context"]:
                task_id = "This request came directly from a device, no task_id."
                task_type = "DeviceRequest"
            else:
                task_id = str(request["request_context"]["task_id"])
                task_type = task_view.get_task(request["request_context"]["task_id"])[
                    "type"
                ]
        else:
            eid = str(request["request_context"]["experiment_id"])
            experiment_name = experiment_view.get_experiment(
                request["request_context"]["experiment_id"]
            )["name"]
            task_id = str(request["request_context"]["task_id"])
            task_type = task_view.get_task(request["request_context"]["task_id"])[
                "type"
            ]

        if eid not in user_input_requests:
            user_input_requests[eid] = []
            id_to_name[eid] = experiment_name

        user_input_requests[eid].append(
            {
                "id": str(request["_id"]),
                "prompt": request["prompt"],
                "task": {
                    "id": task_id,
                    "type": task_type,
                },
                "options": request["options"],
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
