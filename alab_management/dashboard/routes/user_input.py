from bson import ObjectId
from bson.errors import InvalidId
from flask import Blueprint, request
from pydantic import ValidationError

from alab_management.user_input import UserRequestStatus
from ..lab_views import user_input_view, experiment_view

userinput_bp = Blueprint("/userinput", __name__, url_prefix="/api/userinput")


@userinput_bp.route("/pending", methods=["GET"])
def get_userinput_status():
    """
    Get all the status in the database
    """
    user_input_requests = user_input_view.get_all_pending_requests()
    user_input_requests = [
        {
            "id": str(request["_id"]),
            "prompt": request["prompt"],
            "task_id": str(request["task_id"]),
            "experiment_id": str(request["experiment_id"]),
            "experiment_name": experiment_view.get_experiment_by_id(
                request["experiment_id"]
            )["name"],
            "options": request["options"],
        }
        for request in user_input_requests
    ]
    return {"pending_requests": user_input_requests}


@userinput_bp.route("/submit", methods=["POST"])
def submit_user_input():
    """
    Update status of user input request
    """
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
    """
    Find an user input request by idresponse
    """
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
