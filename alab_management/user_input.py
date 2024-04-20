import time
from enum import Enum
from typing import Any, cast

from bson import ObjectId

from alab_management.alarm import Alarm
from alab_management.experiment_view.experiment_view import ExperimentView
from alab_management.task_view import TaskView
from alab_management.utils.data_objects import get_collection

from .config import AlabOSConfig

CONFIG = AlabOSConfig()


class UserRequestStatus(Enum):
    """Enum for user response."""

    FULLFILLED = "fulfilled"
    PENDING = "pending"
    ERROR = "error"


class UserInputView:
    """Sample view manages the samples and their positions."""

    def __init__(self):
        self._input_collection = get_collection("user_input")
        self._task_view = TaskView()
        self._experiment_view = ExperimentView()
        alarm_config = AlabOSConfig().get("alarm", {})
        self._alarm = Alarm(**alarm_config)

    def insert_request(
        self,
        prompt: str,
        options: list[str],
        task_id: ObjectId | None = None,
        maintenance: bool = False,
        category: str = "Unknown Category",
    ) -> ObjectId:
        """
        Insert a request into the database.

        Returns the request ObjectID
        """
        context = {"maintenance": maintenance}
        if task_id is None and not maintenance:
            raise ValueError("task_id is required for non-maintenance requests!")
        if task_id is not None:
            self._task_view.get_task(
                task_id=task_id
            )  # will throw error if task id does not exist
            experiment_id = self._experiment_view.get_experiment_by_task_id(task_id)[
                "_id"
            ]
            context.update(
                {
                    "experiment_id": experiment_id,
                    "task_id": task_id,
                }
            )
        request_id = ObjectId()
        self._input_collection.insert_one(
            {
                "_id": request_id,
                "prompt": prompt,
                "options": [str(opt) for opt in options],
                "status": UserRequestStatus.PENDING.value,
                "request_context": context,
            }
        )
        if maintenance is True:
            category = "Maintenance"
        self._alarm.alert(f"User input requested: {prompt}", category)
        return request_id

    def get_request(self, request_id: ObjectId) -> dict[str, Any]:
        """
        Get a request.

        Returns a request.
        """
        request = self._input_collection.find_one({"_id": request_id})

        if request is None:
            raise ValueError(f"User input request id {request_id} does not exist!")
        return cast(dict[str, Any], request)

    def update_request_status(self, request_id: ObjectId, response: str, note: str):
        """Update the status of a request."""
        self.get_request(request_id)  # will error is request does not exist
        self._input_collection.update_one(
            {"_id": request_id},
            {
                "$set": {
                    "response": response,
                    "note": note,
                    "status": UserRequestStatus.FULLFILLED.value,
                }
            },
        )
        # Wait until the status is updated
        while (
            self.get_request(request_id)["status"] != UserRequestStatus.FULLFILLED.value
        ):
            time.sleep(1)

    def retrieve_user_input(self, request_id: ObjectId) -> str:
        """
        Retrive response from user for a given request. Blocks until request is marked as completed.

        Returns the user response, which is one of a list of options
        """
        status = UserRequestStatus.PENDING
        while status == UserRequestStatus.PENDING:
            request = self._input_collection.find_one({"_id": request_id})
            if request is None:
                raise ValueError(f"User input request id {request_id} does not exist!")
            status = UserRequestStatus(request["status"])
            time.sleep(1)
        return request["response"]

    def clean_up_user_input_collection(self):
        """Drop the sample position collection."""
        self._input_collection.drop()

    def get_all_pending_requests(self) -> list:
        """
        Get all pending requests.

        Returns a list of pending requests.
        """
        return cast(
            list[dict[str, Any]],
            self._input_collection.find({"status": UserRequestStatus.PENDING.value}),
        )


def request_user_input(
    task_id: ObjectId | None,
    prompt: str,
    options: list[str],
    maintenance: bool = False,
    category: str = "Unknown Category",
) -> str:
    """
    Request user input through the dashboard. Blocks until response is given.

    task_id (ObjectId): task id requesting user input
    prompt (str): prompt to give user
    options (List[str]): response options to give user
    maintenance (bool): if true, mark this as a request for overall system maintenance

    Returns user response as string.
    """
    user_input_view = UserInputView()
    request_id = user_input_view.insert_request(
        task_id=task_id,
        prompt=prompt,
        options=options,
        maintenance=maintenance,
        category=category,
    )
    return user_input_view.retrieve_user_input(request_id=request_id)


def request_maintenance_input(prompt: str, options: list[str]):
    """
    Request user input through the dashboard. Blocks until response is given.

    Args:
        prompt: prompt to give user
        options: response options to give user
    """
    return request_user_input(
        task_id=None,
        prompt=prompt,
        options=options,
        maintenance=True,
        category="Maintenance",
    )
