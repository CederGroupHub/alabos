"""
TaskLauncher is the core module of the system,
which actually executes the tasks.
"""

import time
from concurrent.futures import Future
from datetime import datetime
from threading import Thread
from traceback import print_exc
from typing import Any, Dict, List, Optional, Type, Union, cast

import dill
from bson import ObjectId
from pydantic import BaseModel, root_validator

from alab_management.device_view.device import BaseDevice
from alab_management.sample_view.sample import SamplePosition
from alab_management.sample_view.sample_view import SamplePositionRequest
from alab_management.task_view import TaskPriority
from alab_management.utils.data_objects import get_collection

from .enums import _EXTRA_REQUEST, RequestStatus

_SampleRequestDict = Dict[str, int]
_ResourceRequestDict = Dict[
    Optional[Union[Type[BaseDevice], str]], _SampleRequestDict
]  # the raw request sent by task process


class ResourcesRequest(BaseModel):
    """
    This class is used to validate the resource request. Each request should have a format of
    [
        {
            "device":{
                "identifier": "name" or "type" or "nodevice",
                "content": string corresponding to identifier
            },
            "sample_positions": [
                {
                    "prefix": prefix of sample position,
                    "number": integer number of such positions requested.
                },
                ...
            ]
        },
        ...
    ].

    See Also
    --------
        :py:class:`SamplePositionRequest <alab_management.sample_view.sample_view.SamplePositionRequest>`
    """

    __root__: List[
        Dict[str, Union[List[Dict[str, Union[str, int]]], Dict[str, str]]]
    ]  # type: ignore

    @root_validator(pre=True, allow_reuse=True)
    def preprocess(cls, values):
        """Preprocess the request."""
        values = values["__root__"]

        new_values = []
        for request_dict in values:
            if request_dict["device"]["identifier"] not in [
                "name",
                "type",
                _EXTRA_REQUEST,
            ]:
                raise ValueError(
                    f"device identifier must be one of 'name', 'type', or {_EXTRA_REQUEST}"
                )
            new_values.append(
                {
                    "device": {
                        "identifier": request_dict["device"]["identifier"],
                        "content": request_dict["device"]["content"],
                    },
                    "sample_positions": request_dict["sample_positions"],
                }
            )
        return {"__root__": new_values}


class RequestMixin:
    """Simple wrapper for the request collection."""

    def __init__(self):
        self._request_collection = get_collection("requests")

    def update_request_status(self, request_id: ObjectId, status: RequestStatus):
        """Update the status of a request by request_id."""
        return self._request_collection.update_one(
            {"_id": request_id}, {"$set": {"status": status.name}}
        )

    def get_request(self, request_id: ObjectId, **kwargs):
        """Get a request by request_id."""
        return self._request_collection.find_one(
            {"_id": request_id}, **kwargs
        )  # DB_ACCESS_OUTSIDE_VIEW

    def get_requests_by_status(self, status: RequestStatus):
        """Get all requests by status."""
        return self._request_collection.find(
            {"status": status.name}
        )  # DB_ACCESS_OUTSIDE_VIEW

    def get_requests_by_task_id(self, task_id: ObjectId):
        """Get all requests by task_id."""
        return self._request_collection.find({"task_id": task_id})


class ResourceRequester(RequestMixin):
    """
    Class for request lab resources easily. This class will insert a request into the database,
    and then the task manager will read from the database and assign the resources.

    It is used in :py:class:`~alab_management.lab_view.LabView`.
    """

    def __init__(
        self,
        task_id: ObjectId,
    ):
        self._request_collection = get_collection("requests")
        self._waiting: Dict[ObjectId, Dict[str, Any]] = {}
        self.task_id = task_id
        self.priority: Union[int, TaskPriority] = (
            TaskPriority.NORMAL
        )  # will usually be overwritten by BaseTask instantiation.

        super().__init__()
        self._stop = False
        self._thread = Thread(
            target=self._check_request_status_loop, name="CheckRequestStatus"
        )
        self._thread.daemon = True
        self._thread.start()

    def __close__(self):
        """Close the thread."""
        self._stop = True
        self._thread.join()

    __del__ = __close__

    def request_resources(
        self,
        resource_request: _ResourceRequestDict,
        timeout: Optional[float] = None,
        priority: Optional[Union[TaskPriority, int]] = None,
    ) -> Dict[str, Any]:
        """
        Request lab resources.

        Write the request into the database, and then the task manager will read from the
        database and assign the resources.
        """
        f = Future()
        if priority is None:
            priority = self.priority

        formatted_resource_request = []

        device_str_to_request = {}
        for device, position_dict in resource_request.items():
            if device is None:
                identifier = _EXTRA_REQUEST
                content = _EXTRA_REQUEST
            elif isinstance(device, str):
                identifier = "name"
                content = device
            elif issubclass(device, BaseDevice):
                identifier = "type"
                content = device.__name__
            else:
                raise ValueError(
                    "device must be a name of a specific device, a class of type BaseDevice, or None"
                )
            device_str_to_request[content] = device

            positions = [
                dict(SamplePositionRequest(prefix=prefix, number=number))
                for prefix, number in position_dict.items()
            ]  # immediate dict conversion - SamplePositionRequest is only used to check request format.
            formatted_resource_request.append(
                {
                    "device": {
                        "identifier": identifier,
                        "content": content,
                    },
                    "sample_positions": positions,
                }
            )

        if not isinstance(formatted_resource_request, ResourcesRequest):
            formatted_resource_request = ResourcesRequest(__root__=formatted_resource_request)  # type: ignore
        formatted_resource_request = formatted_resource_request.dict()["__root__"]

        result = self._request_collection.insert_one(
            {
                "request": formatted_resource_request,
                "status": RequestStatus.PENDING.name,
                "task_id": self.task_id,
                "priority": int(priority),
                "submitted_at": datetime.now(),
            }
        )  # DB_ACCESS_OUTSIDE_VIEW
        _id: ObjectId = cast(ObjectId, result.inserted_id)
        self._waiting[_id] = {"f": f, "device_str_to_request": device_str_to_request}

        try:
            result = f.result(timeout=timeout)
        except TimeoutError:  # cancel the task if timeout
            self.update_request_status(request_id=_id, status=RequestStatus.CANCELED)
            raise
        return {
            **self._post_process_requested_resource(
                devices=result["devices"],
                sample_positions=result["sample_positions"],
                resource_request=resource_request,
            ),
            "request_id": result["request_id"],
        }

    def release_resources(self, request_id: ObjectId) -> bool:
        """Release a request by request_id."""
        result = self._request_collection.update_one(
            {
                "_id": request_id,
                "status": RequestStatus.FULFILLED.name,
            },
            {
                "$set": {
                    "status": RequestStatus.NEED_RELEASE.name,
                }
            },
        )

        return result.modified_count == 1

    def release_all_resources(self):
        """
        Release all requests by task_id, used for error recovery.

        For the requests that are not fulfilled, they will be marked as CANCELED.

        For the request that have been fulfilled, they will be marked as NEED_RELEASE.
        """
        self._request_collection.update_many(
            {
                "task_id": self.task_id,
                "status": RequestStatus.FULFILLED.name,
            },
            {
                "$set": {
                    "status": RequestStatus.NEED_RELEASE.name,
                }
            },
        )

        self._request_collection.update_many(
            {
                "task_id": self.task_id,
                "status": RequestStatus.PENDING.name,
            },
            {
                "$set": {
                    "status": RequestStatus.CANCELED.name,
                }
            },
        )

    def _check_request_status_loop(self):
        while not self._stop:
            try:
                for request_id in self._waiting.copy():
                    status = self.get_request(request_id=request_id, projection=["status"])["status"]  # type: ignore
                    if status == RequestStatus.FULFILLED.name:
                        self._handle_fulfilled_request(request_id=request_id)
                    elif status == RequestStatus.ERROR.name:
                        self._handle_error_request(request_id=request_id)
            except Exception:
                print_exc()  # for debugging in the test
                raise
            time.sleep(0.5)

    def _handle_fulfilled_request(self, request_id: ObjectId):
        entry = self.get_request(request_id)
        if entry["status"] != RequestStatus.FULFILLED.name:  # type: ignore
            return

        assigned_devices: Dict[str, Dict[str, Union[str, bool]]] = entry["assigned_devices"]  # type: ignore
        assigned_sample_positions: Dict[str, List[Dict[str, Any]]] = entry["assigned_sample_positions"]  # type: ignore

        request: Dict[str, Any] = self._waiting.pop(request_id)

        f: Future = request["f"]
        device_str_to_request: Dict[str, Union[Type[BaseDevice], str, None]] = request[
            "device_str_to_request"
        ]

        f.set_result(
            {
                "devices": {
                    device_str_to_request[device_str]: device_dict["name"]
                    for device_str, device_dict in assigned_devices.items()
                },
                "sample_positions": {
                    name: [
                        sample_position["name"]
                        for sample_position in sample_positions_list
                    ]
                    for name, sample_positions_list in assigned_sample_positions.items()
                },
                "request_id": request_id,
            }
        )

    def _handle_error_request(self, request_id: ObjectId):
        entry = self.get_request(request_id)
        if entry["status"] != RequestStatus.ERROR.name:  # type: ignore
            return

        error: Exception = dill.loads(entry["error"])  # type: ignore
        request: Dict[str, Any] = self._waiting.pop(request_id)
        f: Future = request["f"]
        f.set_exception(error)

    @staticmethod
    def _post_process_requested_resource(
        devices: Dict[Type[BaseDevice], str],
        sample_positions: Dict[str, List[str]],
        resource_request: Dict[str, List[Dict[str, Union[int, str]]]],
    ):
        processed_sample_positions: Dict[
            Optional[Type[BaseDevice]], Dict[str, List[str]]
        ] = {}

        for device_request, sample_position_dict in resource_request.items():
            if len(sample_position_dict) == 0:
                continue
            processed_sample_positions[device_request] = {}
            for prefix in sample_position_dict:
                reply_prefix = prefix
                if device_request is None:  # no device name to prepend
                    pass
                else:
                    device_prefix = (
                        f"{devices[device_request]}{SamplePosition.SEPARATOR}"
                    )
                    if not reply_prefix.startswith(
                        device_prefix
                    ):  # dont extra prepend for nested requests
                        reply_prefix = device_prefix + reply_prefix
                processed_sample_positions[device_request][prefix] = sample_positions[
                    reply_prefix
                ]
                # {
        #     device_request: {
        #         prefix: sample_positions[prefix] for prefix in sample_position_dict
        #     }
        #     for device_request, sample_position_dict in resource_request.items()
        # }
        return {
            "devices": devices,
            "sample_positions": processed_sample_positions,
        }
