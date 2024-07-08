"""
TaskLauncher is the core module of the system,
which actually executes the tasks.
"""

import multiprocessing
import time
from datetime import datetime
from traceback import format_exc
from typing import Any, cast

import dill
from bson import ObjectId

from alab_management.device_view.device_view import DeviceView
from alab_management.logger import DBLogger
from alab_management.resource_manager.enums import _EXTRA_REQUEST
from alab_management.resource_manager.resource_requester import (
    RequestMixin,
    RequestStatus,
)
from alab_management.sample_view.sample import SamplePosition
from alab_management.sample_view.sample_view import SamplePositionRequest, SampleView
from alab_management.task_view import TaskView
from alab_management.task_view.task_enums import CancelingProgress, TaskStatus
from alab_management.utils.data_objects import DocumentNotUpdatedError, get_collection
from alab_management.utils.module_ops import load_definition
from alab_management.utils.versioning import get_version


class ResourceManager(RequestMixin):
    """
    TaskManager will.

    (1) find all the ready tasks and submit them,
    (2) handle all the resource requests
    """

    def __init__(self, live_time: float | None = None, termination_event=None):
        load_definition(get_version())
        self.task_view = TaskView()
        self.sample_view = SampleView()
        self.device_view = DeviceView()
        self._request_collection = get_collection("requests")

        self.logger = DBLogger(task_id=None)
        super().__init__()
        time.sleep(1)  # allow some time for other modules to launch
        self.live_time = live_time
        self.termination_event = termination_event or multiprocessing.Event()

    def run(self):
        """Start the loop."""
        start = time.time()
        while not self.termination_event.is_set() and (
            self.live_time is None or time.time() - start < self.live_time
        ):
            self._loop()
            time.sleep(0.5)

    def _loop(self):
        self.handle_released_resources()
        self.handle_requested_resources()

    def handle_released_resources(self):
        """Release the resources."""
        for request in self.get_requests_by_status(RequestStatus.NEED_RELEASE):
            devices = request["assigned_devices"]
            sample_positions = request["assigned_sample_positions"]
            self._release_devices(devices)
            self._release_sample_positions(sample_positions)
            self.update_request_status(
                request_id=request["_id"],
                status=RequestStatus.RELEASED,
                original_status=RequestStatus.NEED_RELEASE,
            )

    def handle_requested_resources(self):
        """
        Check if there are any requests that are in PENDING status. If so,
        try to assign the resources to it.
        """
        requests = list(self.get_requests_by_status(RequestStatus.PENDING))
        # prioritize the oldest requests at the highest priority value
        requests.sort(key=lambda x: x["submitted_at"])
        requests.sort(key=lambda x: x["priority"], reverse=True)
        for request in requests:
            self._handle_requested_resources(request)

    def _handle_requested_resources(self, request_entry: dict[str, Any]):
        try:
            resource_request = request_entry["request"]
            task_id = request_entry["task_id"]

            task_status = self.task_view.get_status(task_id=task_id)
            if task_status != TaskStatus.REQUESTING_RESOURCES or task_id in {
                task["task_id"]
                for task in self.task_view.get_tasks_to_be_canceled(
                    canceling_progress=CancelingProgress.WORKER_NOTIFIED
                )
            }:
                # this implies the Task has been cancelled or errored somewhere else in the chain -- we should
                # not allocate any resources to the broken Task.
                self.update_request_status(
                    request_id=request_entry["_id"],
                    status=RequestStatus.CANCELED,
                    original_status=RequestStatus.PENDING,
                )
                return

            devices = self.device_view.request_devices(
                task_id=task_id,
                device_names_str=[
                    entry["device"]["content"]
                    for entry in resource_request
                    if entry["device"]["identifier"] == "name"
                ],
                device_types_str=[
                    entry["device"]["content"]
                    for entry in resource_request
                    if entry["device"]["identifier"] == "type"
                ],
            )
            # some devices are not available now
            # the request cannot be fulfilled
            if devices is None:
                return

            # replace device placeholder in sample position request
            # and make it into a single list
            parsed_sample_positions_request = []
            for request in resource_request:
                if request["device"]["identifier"] == _EXTRA_REQUEST:
                    device_prefix = ""
                else:
                    device_name = devices[request["device"]["content"]]["name"]
                    device_prefix = f"{device_name}{SamplePosition.SEPARATOR}"

                for pos in request["sample_positions"]:
                    prefix = pos["prefix"]
                    # if this is a nested resource request, lets not prepend the device name twice.
                    if not prefix.startswith(device_prefix):
                        prefix = device_prefix + prefix
                    parsed_sample_positions_request.append(
                        SamplePositionRequest(prefix=prefix, number=pos["number"])
                    )

            self._request_collection.update_one(
                {"_id": request_entry["_id"]},
                {
                    "$set": {
                        "parsed_sample_positions_request": [
                            dict(spr) for spr in parsed_sample_positions_request
                        ]
                    }
                },
            )
            sample_positions = self.sample_view.request_sample_positions(
                task_id=task_id, sample_positions=parsed_sample_positions_request
            )
            if sample_positions is None:
                return

        # in case some errors happen, we will raise the error in the task process instead of the main process
        except Exception as error:  # pylint: disable=broad-except
            # we will store the error in the database for easier debugging
            error.args = (format_exc(),)
            returned_value = self._request_collection.update_one(
                {"_id": request_entry["_id"], "status": RequestStatus.PENDING.name},
                {
                    "$set": {
                        "status": RequestStatus.ERROR.name,
                        "error": dill.dumps(error),
                        "assigned_devices": None,
                        "assigned_sample_positions": None,
                    }
                },
            )
            if returned_value.modified_count != 1:
                raise DocumentNotUpdatedError(
                    f"Error updating request {request_entry['_id']}: cannot update the request status from PENDING "
                    f"to ERROR."
                ) from error
            return

        # if both devices and sample positions can be satisfied
        returned_value = self._request_collection.update_one(
            {"_id": request_entry["_id"], "status": RequestStatus.PENDING.name},
            {
                "$set": {
                    "assigned_devices": devices,
                    "assigned_sample_positions": sample_positions,
                    "status": RequestStatus.FULFILLED.name,
                    "fulfilled_at": datetime.now(),
                }
            },
        )
        if returned_value.modified_count == 1:
            # label the resources as occupied
            self._occupy_devices(devices=devices, task_id=task_id)
            self._occupy_sample_positions(
                sample_positions=sample_positions, task_id=task_id
            )

    def _occupy_devices(self, devices: dict[str, dict[str, Any]], task_id: ObjectId):
        for device in devices.values():
            self.device_view.occupy_device(
                device=cast(str, device["name"]), task_id=task_id
            )

    def _occupy_sample_positions(
        self, sample_positions: dict[str, list[dict[str, Any]]], task_id: ObjectId
    ):
        for sample_positions_ in sample_positions.values():
            for sample_position_ in sample_positions_:
                self.sample_view.lock_sample_position(
                    task_id, cast(str, sample_position_["name"])
                )

    def _release_devices(self, devices: dict[str, dict[str, Any]]):
        for device in devices.values():
            if device["need_release"]:
                self.device_view.release_device(device["name"])

    def _release_sample_positions(
        self, sample_positions: dict[str, list[dict[str, Any]]]
    ):
        for sample_positions_ in sample_positions.values():
            for sample_position in sample_positions_:
                if sample_position["need_release"]:
                    self.sample_view.release_sample_position(sample_position["name"])
