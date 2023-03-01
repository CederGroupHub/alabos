from bson import ObjectId
from flask import Blueprint

from ..lab_views import (
    task_view,
)
from ...task_view import TaskStatus

task_bp = Blueprint("/task", __name__, url_prefix="/api/task")


@task_bp.route("/cancel/<task_id>", methods=["GET"])
def cancel_task(task_id: str):
    """
    API to cancel a task
    """
    try:
        task_id: ObjectId = ObjectId(task_id)
        task_view.mark_task_as_cancelling(task_id)

        return {
            "status": "success"
        }
    except Exception as exception:
        return {"status": "error", "errors": exception.args[0]}, 400
