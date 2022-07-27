import time
from alab_management.utils.data_objects import get_collection
from enum import Enum
from bson import ObjectId
from alab_management.task_view import TaskView


class UserRequestStatus(Enum):
    """
    Enum for user response.
    """

    SUCCESS = "success"
    PENDING = "pending"
    ERROR = "error"


def _insert_request(task_id: ObjectId, prompt: str) -> ObjectId:
    """
    Insert a request into the database.

    Returns the request ObjectID
    """
    task_view = TaskView(task_id=task_id)
    task_view.get_task(task_id=task_id)  # will throw error if task id does not exist

    coll = get_collection("user_input")
    request_id = ObjectId()
    coll.insert_one(
        {
            "_id": request_id,
            "prompt": prompt,
            "task_id": task_id,
            "status": UserRequestStatus.PENDING.value,
        }
    )
    return request_id


def _wait_for_user_input(request_id: ObjectId) -> UserRequestStatus:
    """
    Wait for user input.

    Returns the user response.
    """
    coll = get_collection("user_input")
    status = UserRequestStatus.PENDING
    while status == UserRequestStatus.PENDING:
        request = coll.find_one({"_id": request_id})
        if request is None:
            raise ValueError(f"User input request id {request_id} does not exist!")
        status = UserRequestStatus(request["status"])
        time.sleep(1)
    return status


def request_user_input(task_id: ObjectId, prompt: str) -> UserRequestStatus:
    """
    Request user input through the dashboard. Blocks until response is given.

    Returns user response.
    """
    request_id = _insert_request(task_id=task_id, prompt=prompt)
    return _wait_for_user_input(request_id=request_id)
