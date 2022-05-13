"""
TaskLauncher is the core module of the system,
which actually executes the tasks
"""
import re
import time
from concurrent.futures import Future
from enum import Enum, auto
from threading import Thread
from traceback import print_exc
from typing import Union, Dict, Optional, Type, List, Any, cast

import dill
from bson import ObjectId
from pydantic import BaseModel, root_validator

from .device_view import DeviceView
from .device_view.device import BaseDevice
from .sample_view import SampleView
from .sample_view.sample_view import SamplePositionRequest
from .task_actor import run_task
from .task_view.task_view import TaskView
from .utils.data_objects import get_collection
from .utils.module_ops import load_definition

_SampleRequestDict = Union[str, Dict[str, Union[str, int]]]
_ResourceRequestDict = \
    Dict[Optional[Type[BaseDevice]], List[_SampleRequestDict]]  # the raw request sent by task process

_EXTRA_REQUEST: str = "__extras"


class RequestStatus(Enum):
    """
    The status for a request. It will be stored in the database
    """
    PENDING = auto()
    FULFILLED = auto()
    NEED_RELEASE = auto()
    RELEASED = auto()
    CANCELED = auto()
    ERROR = auto()


class ResourcesRequest(BaseModel):
    """
    This class is used to validate the resource request. Each request should have a format of
    [DeviceType: List of SamplePositionRequest]

    See Also:
        :py:class:`SamplePositionRequest <alab_management.sample_view.sample_view.SamplePositionRequest>`
    """
    __root__: Dict[str, List[SamplePositionRequest]]  # type: ignore

    @root_validator(pre=True, allow_reuse=True)
    def preprocess(cls, values):  # pylint: disable=no-self-use,no-self-argument
        values = values["__root__"]
        # if the sample position request is string, we will automatically add a number attribute = 1.
        values = {k: [SamplePositionRequest.from_str(v_)
                      if isinstance(v_, str) else v_
                      for v_ in v] for k, v in values.items()}
        return {"__root__": values}


class RequestMixin:
    """
    Simple wrapper for the request collection
    """
    def __init__(self):
        self._request_collection = get_collection("requests")

    def update_request_status(self, request_id: ObjectId, status: RequestStatus):
        return self._request_collection.update_one({"_id": request_id}, {"$set": {
            "status": status.name
        }})

    def get_request(self, request_id: ObjectId, **kwargs):
        return self._request_collection.find_one({"_id": request_id}, **kwargs)

    def get_request_with_status(self, status: RequestStatus):
        return self._request_collection.find({"status": status.name})


class TaskManager(RequestMixin):
    """
    TaskManager will

    (1) find all the ready tasks and submit them,
    (2) handle all the resource requests
    """

    def __init__(self):
        load_definition()
        self.task_view = TaskView()
        self.sample_view = SampleView()
        self.device_view = DeviceView()
        super().__init__()
        time.sleep(1)  # allow some time for other modules to launch

    def run(self):
        """
        Start the loop
        """
        while True:
            self._loop()
            time.sleep(0.5)

    def _loop(self):
        self.submit_ready_tasks()
        self.handle_released_resources()
        self.handle_requested_resources()

    def submit_ready_tasks(self):
        """
        Checking if there are any tasks that are ready to be submitted. (STATUS = READY)
        If so, submit them to task actor (dramatiq worker).
        """
        ready_task_entries = self.task_view.get_ready_tasks()
        for task_entry in ready_task_entries:
            run_task.send(task_id_str=str(task_entry["task_id"]))

    def handle_released_resources(self):
        """
        Release the resources.
        """
        for request in self.get_request_with_status(RequestStatus.NEED_RELEASE):
            devices = request["assigned_devices"]
            sample_positions = request["assigned_sample_positions"]
            self._release_devices(devices)
            self._release_sample_positions(sample_positions)
            self.update_request_status(request_id=request["_id"], status=RequestStatus.RELEASED)

    def handle_requested_resources(self):
        """
        Check if there are any requests that are in PENDING status. If so,
        try to assign the resources to it.
        """
        # TODO: add priority here (some sort function)
        for request in self.get_request_with_status(RequestStatus.PENDING):
            self._handle_requested_resources(request)

    def _handle_requested_resources(self, request_entry: Dict[str, Any]):
        try:
            resource_request = request_entry["request"]
            task_id = request_entry["task_id"]

            devices = self.device_view.request_devices(task_id=task_id, device_types_str=[
                device_type for device_type in resource_request.keys()
                if device_type != _EXTRA_REQUEST
            ])
            # some devices are not available now
            # the request cannot be fulfilled
            if devices is None:
                return

            # replace device placeholder in sample position request
            # and make it into a single list
            parsed_sample_positions_request = []
            for device_type, device in devices.items():
                device_name = device["name"]
                parsed_sample_positions_request.extend([
                    {**sample_position_request,
                     "prefix": re.sub(r"\$", device_name, sample_position_request["prefix"])}  # type: ignore
                    for sample_position_request in resource_request[device_type]])

            if any("$" in sample_position_request["prefix"]
                   for sample_position_request in resource_request.get(_EXTRA_REQUEST, [])):
                raise ValueError("$ should not appear under `None`, which is actually not a device.")
            parsed_sample_positions_request.extend(resource_request.get(_EXTRA_REQUEST, []))
            sample_positions = self.sample_view.request_sample_positions(
                task_id=task_id,
                sample_positions=[SamplePositionRequest(**request) for request in parsed_sample_positions_request],
            )

            if sample_positions is None:
                return

        # in case some errors happen, we will raise the error in the task process instead of the main process
        except Exception as error:  # pylint: disable=broad-except
            self._request_collection.update_one({"_id": request_entry["_id"]}, {"$set": {
                "status": RequestStatus.ERROR.name,
                "error": dill.dumps(error),
                "assigned_devices": None,
                "assigned_sample_positions": None,
            }})
            return

        # if both devices and sample positions can be satisfied
        self._request_collection.update_one({"_id": request_entry["_id"]}, {"$set": {
            "assigned_devices": devices,
            "assigned_sample_positions": sample_positions,
            "status": RequestStatus.FULFILLED.name,
        }})
        # label the resources as occupied
        self._occupy_devices(devices=devices, task_id=task_id)
        self._occupy_sample_positions(sample_positions=sample_positions, task_id=task_id)

    def _occupy_devices(self, devices: Dict[str, Dict[str, Any]], task_id: ObjectId):
        for device in devices.values():
            self.device_view.occupy_device(device=cast(str, device["name"]), task_id=task_id)

    def _occupy_sample_positions(self, sample_positions: Dict[str, List[Dict[str, Any]]], task_id: ObjectId):
        for sample_positions_ in sample_positions.values():
            for sample_position_ in sample_positions_:
                self.sample_view.lock_sample_position(task_id, cast(str, sample_position_["name"]))

    def _release_devices(self, devices: Dict[str, Dict[str, Any]]):
        for device in devices.values():
            if device["need_release"]:
                self.device_view.release_device(device["name"])

    def _release_sample_positions(self, sample_positions: Dict[str, List[Dict[str, Any]]]):
        for sample_positions_ in sample_positions.values():
            for sample_position in sample_positions_:
                if sample_position["need_release"]:
                    self.sample_view.release_sample_position(sample_position["name"])


class ResourceRequester(RequestMixin):
    """
    Class for request lab resources easily. This class will insert a request into the database,
    and then the task manager will read from the database and assign the resources.

    It is used in :py:class:`~alab_management.lab_view.LabView`.
    """
    def __init__(self, task_id: ObjectId):
        self._request_collection = get_collection("requests")
        self._waiting: Dict[ObjectId, Dict[str, Any]] = {}
        self.task_id = task_id
        super().__init__()

        self._thread = Thread(target=self._check_request_status_loop)
        self._thread.daemon = True
        self._thread.start()

    def request_resources(self, resource_request: _ResourceRequestDict,
                          timeout: Optional[float] = None) -> Dict[str, Any]:
        """
        Request lab resources. Write the request into the database, and then the task manager will read from the
        database and assign the resources.
        """
        f = Future()

        formatted_resource_request = {device_type.__name__: samples for device_type, samples in resource_request.items()
                                      if device_type is not None}
        if None in resource_request:
            formatted_resource_request[_EXTRA_REQUEST] = resource_request[None]

        if not isinstance(formatted_resource_request, ResourcesRequest):
            formatted_resource_request = ResourcesRequest(__root__=formatted_resource_request)  # type: ignore
        formatted_resource_request = formatted_resource_request.dict()["__root__"]

        result = self._request_collection.insert_one({"request": formatted_resource_request,
                                                      "status": RequestStatus.PENDING.name,
                                                      "task_id": self.task_id})
        _id: ObjectId = cast(ObjectId, result.inserted_id)

        self._waiting[_id] = {
            "f": f,
            "raw_request": resource_request,
        }

        try:
            result = f.result(timeout=timeout)
        except TimeoutError:
            # cancel the task
            self.update_request_status(request_id=_id, status=RequestStatus.CANCELED)
            raise

        return {
            **self._post_process_requested_resource(
                devices=result["devices"],
                sample_positions=result["sample_positions"],
                resource_request=formatted_resource_request
            ),
            "request_id": result["request_id"],
        }

    def release_resources(self, request_id: ObjectId) -> bool:
        """
        Release a request by request_id
        """
        result = self._request_collection.update_one({
            "_id": request_id,
            "status": RequestStatus.FULFILLED.name,
        }, {"$set": {
            "status": RequestStatus.NEED_RELEASE.name,
        }})

        return result.modified_count == 1

    def _check_request_status_loop(self):
        while True:
            try:
                for request_id in self._waiting.copy().keys():
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
        raw_request = request["raw_request"]

        device_str_to_type: Dict[str, Type[BaseDevice]] = {device_type.__name__: device_type
                                                           for device_type in raw_request if device_type is not None}

        f.set_result({
            "devices": {device_str_to_type[device_type_str]: device_dict["name"]
                        for device_type_str, device_dict in assigned_devices.items()},
            "sample_positions": {name: [sample_position["name"] for sample_position in sample_positions_list]
                                 for name, sample_positions_list in assigned_sample_positions.items()},
            "request_id": request_id,
        })

    def _handle_error_request(self, request_id: ObjectId):
        entry = self.get_request(request_id)
        if entry["status"] != RequestStatus.ERROR.name:  # type: ignore
            return

        error: Exception = dill.loads(entry["error"])  # type: ignore
        request: Dict[str, Any] = self._waiting.pop(request_id)
        f: Future = request["f"]
        f.set_exception(error)

    @staticmethod
    def _post_process_requested_resource(devices: Dict[Type[BaseDevice], str], sample_positions: Dict[str, List[str]],
                                         resource_request: Dict[str, List[Dict[str, Union[int, str]]]]):
        processed_sample_positions: Dict[Optional[Type[BaseDevice]], Dict[str, List[str]]] = {}

        for device_type, device_str in devices.items():  # type: ignore
            sample_position_requests = resource_request[device_type.__name__]
            processed_sample_positions[device_type] = {
                cast(str, sample_position_request["prefix"]): sample_positions.pop(
                    cast(str, sample_position_request["prefix"]).replace("$", device_str))
                for sample_position_request in sample_position_requests
            }
        if _EXTRA_REQUEST in resource_request:
            processed_sample_positions[None] = {
                cast(str, sample_position_request["prefix"]):
                    sample_positions.pop(cast(str, sample_position_request["prefix"]))
                for sample_position_request in resource_request[_EXTRA_REQUEST]
            }
        return {
            "devices": devices,
            "sample_positions": processed_sample_positions,
        }
