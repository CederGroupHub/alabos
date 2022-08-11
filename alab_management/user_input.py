import time
from typing import Any, Dict, List, cast
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


class UserInputView:
    """
    Sample view manages the samples and their positions
    """

    def __init__(self):
        self._input_collection = get_collection("user_input")
        self._task_view = TaskView()

    def insert_request(self, task_id: ObjectId, prompt: str) -> ObjectId:
        """
        Insert a request into the database.

        Returns the request ObjectID
        """
        self._task_view.get_task(
            task_id=task_id
        )  # will throw error if task id does not exist

        request_id = ObjectId()
        self._input_collection.insert_one(
            {
                "_id": request_id,
                "prompt": prompt,
                "task_id": task_id,
                "status": UserRequestStatus.PENDING.value,
            }
        )
        return request_id

    def get_request(self, request_id: ObjectId) -> Dict[str, Any]:
        """
        Get a request.

        Returns a request.
        """
        request = self._input_collection.find_one({"_id": request_id})

        if request is None:
            raise ValueError(f"User input request id {request_id} does not exist!")
        return cast(Dict[str, Any], request)

    def update_request_status(self, request_id: ObjectId, status: UserRequestStatus, note:str):
        """
        Update the status of a request.
        """
        self.get_request(request_id)  # will error is request does not exist
        self._input_collection.update_one(
            {"_id": request_id}, {"$set": {"status": status.value, "note": note}}
        )

    def wait_for_user_input(self, request_id: ObjectId) -> UserRequestStatus:
        """
        Wait for user input.

        Returns the user response.
        """
        status = UserRequestStatus.PENDING
        while status == UserRequestStatus.PENDING:
            request = self._input_collection.find_one({"_id": request_id})
            if request is None:
                raise ValueError(f"User input request id {request_id} does not exist!")
            status = UserRequestStatus(request["status"])
            time.sleep(1)
        return status

    def clean_up_user_input_collection(self):
        """
        Drop the sample position collection
        """
        self._input_collection.drop()

    def get_all_pending_requests(self) -> list:
        """
        Get all pending requests.

        Returns a list of pending requests.
        """

        return cast(
            List[Dict[str, Any]],
            self._input_collection.find({"status": UserRequestStatus.PENDING.value}),
        )


def request_user_input(task_id: ObjectId, prompt: str) -> UserRequestStatus:
    """
    Request user input through the dashboard. Blocks until response is given.

    Returns user response.
    """
    user_input_view = UserInputView()
    request_id = user_input_view.insert_request(task_id=task_id, prompt=prompt)
    return user_input_view.wait_for_user_input(request_id=request_id)
