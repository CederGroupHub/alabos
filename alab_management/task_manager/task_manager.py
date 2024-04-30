"""
TaskLauncher is the core module of the system,
which actually executes the tasks.
"""

import time
from datetime import datetime
from typing import Any, cast

import dill
from bson import ObjectId
from dramatiq_abort import abort

from alab_management.device_view.device_view import DeviceView
from alab_management.lab_view import LabView
from alab_management.logger import DBLogger
from alab_management.sample_view.sample import SamplePosition
from alab_management.sample_view.sample_view import SamplePositionRequest, SampleView
from alab_management.task_actor import run_task
from alab_management.task_manager.enums import _EXTRA_REQUEST
from alab_management.task_manager.resource_requester import (
    RequestMixin,
    RequestStatus,
)
from alab_management.task_view import TaskView
from alab_management.task_view.task_enums import TaskStatus
from alab_management.utils.data_objects import get_collection
from alab_management.utils.module_ops import load_definition


class TaskManager(RequestMixin):
    """
    TaskManager will.

    (1) find all the ready tasks and submit them,
    (2) handle all the resource requests
    """

    def __init__(self):
        load_definition()
        self.task_view = TaskView()
        self.sample_view = SampleView()
        self.device_view = DeviceView()
        self._request_collection = get_collection("requests")

        self.logger = DBLogger(task_id=None)
        super().__init__()
        time.sleep(1)  # allow some time for other modules to launch

    def run(self):
        """Start the loop."""
        while True:
            self._loop()
            time.sleep(1)

    def _loop(self):
        self.handle_tasks_to_be_canceled()
        self.handle_released_resources()
        self.handle_requested_resources()
        self.submit_ready_tasks()

    def _clean_up_tasks_from_previous_runs(self):
        """Cleans up incomplete tasks that exist from the last time the taskmanager was running. Note that this will
        block the task queue until all samples in these tasks have been removed from the physical lab (confirmed via
        user requests on the dashboard).

        This typically occurs if the taskmanager was exited using SIGTERM (ctrl-c), in which case some tasks may
        still be in the RUNNING or CANCELLING state. These will be set to CANCELLED now.
        """
        statuses_to_cancel = [
            TaskStatus.RUNNING,
            TaskStatus.REQUESTING_RESOURCES,
        ]
        tasks_to_cancel = []
        for status in statuses_to_cancel:
            tasks_to_cancel += self.task_view.get_tasks_by_status(status)

        statuses_to_restart = [TaskStatus.INITIATED]
        tasks_to_restart = []
        for status in statuses_to_restart:
            tasks_to_restart += self.task_view.get_tasks_by_status(status)

        for task in tasks_to_restart:
            self.task_view.update_status(
                task_id=task["task_id"], status=TaskStatus.READY
            )

        if len(tasks_to_cancel) == 0:
            print("No dangling tasks found from previous alabos workers. Nice!")
            return

        print(
            f"""
              Found {len(tasks_to_cancel)} dangling tasks leftover from previous alabos workers. These tasks were in
              an unknown state (RUNNING or CANCELLING) when the alabos workers were stopped.

              We will now cancel them and remove their physical components from the lab. We will go through each task
              one by one. A user request will appear on the alabos dashboard for each task. Please acknowledge each
              request to remove the samples from the lab. Once all tasks have been addressed, the alabos workers will
              begin to process new tasks. Lets begin:"""
        )
        for i, task_entry in enumerate(tasks_to_cancel):
            task_id = task_entry["task_id"]
            task_class = task_entry["type"]
            task_name = task_class.__name__

            print(
                f"\n({i + 1}/{len(tasks_to_cancel)}) please clean up task {task_name} ({task_id}) using the ALabOS "
                f"dashboard..."
            )

            # puts a user request on the dashboard to remove all samples in this task from the physical lab,
            # blocks until request is acknowledged. There may be a duplicate request on the dashboard if the task was
            # already cancelled before the taskmanager was restarted. Acknowledging both should be fine.
            LabView(task_id=task_id).request_cleanup()

            # mark task as successfully cancelled
            self.task_view.update_status(task_id=task_id, status=TaskStatus.CANCELLED)
            print("\t Task cancelled successfully.")

        print("Cleanup is done, nice job. Lets get back to work!")

    def submit_ready_tasks(self):
        """
        Checking if there are any tasks that are ready to be submitted. (STATUS = READY)
        If so, submit them to task actor (dramatiq worker).
        """
        ready_task_entries = self.task_view.get_ready_tasks()
        for task_entry in ready_task_entries:
            self.logger.system_log(
                level="DEBUG",
                log_data={
                    "logged_by": self.__class__.__name__,
                    "type": "SendingTaskToActor",
                    "task_id": task_entry["task_id"],
                },
            )
            self.task_view.update_status(
                task_id=task_entry["task_id"], status=TaskStatus.INITIATED
            )
            result = run_task.send_with_options(kwargs={"task_id_str": str(task_entry["task_id"])})
            message_id = result.message_id
            self.task_view.set_task_actor_id(
                task_id=task_entry["task_id"], message_id=message_id
            )

    def handle_tasks_to_be_canceled(self):
        """Check if there are any tasks needs to be stopped."""
        tasks_to_be_cancelled = self.task_view.get_tasks_to_be_canceled()

        for task_entry in tasks_to_be_cancelled:
            self.logger.system_log(
                level="DEBUG",
                log_data={
                    "logged_by": self.__class__.__name__,
                    "type": "CancellingTask",
                    "task_id": task_entry["task_id"],
                    "task_actor_id": task_entry.get("task_actor_id", None),
                },
            )
            if (message_id := task_entry.get("task_actor_id", None)) is not None:
                abort(message_id=message_id)

            # even if the task is not running, we will mark it as cancelled
            self.task_view.update_status(
                task_id=task_entry["task_id"],
                status=TaskStatus.CANCELLED,
            )

    def handle_released_resources(self):
        """Release the resources."""
        for request in self.get_requests_by_status(RequestStatus.NEED_RELEASE):
            devices = request["assigned_devices"]
            sample_positions = request["assigned_sample_positions"]
            self._release_devices(devices)
            self._release_sample_positions(sample_positions)
            self.update_request_status(
                request_id=request["_id"], status=RequestStatus.RELEASED
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
            if task_status != TaskStatus.REQUESTING_RESOURCES:
                # this implies the Task has been cancelled or errored somewhere else in the chain -- we should
                # not allocate any resources to the broken Task.
                self.update_request_status(
                    request_id=resource_request["_id"],
                    status=RequestStatus.CANCELED,
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
            self._request_collection.update_one(
                {"_id": request_entry["_id"]},
                {
                    "$set": {
                        "status": RequestStatus.ERROR.name,
                        "error": dill.dumps(error),
                        "assigned_devices": None,
                        "assigned_sample_positions": None,
                    }
                },
            )
            return

        # if both devices and sample positions can be satisfied
        self._request_collection.update_one(
            {"_id": request_entry["_id"]},
            {
                "$set": {
                    "assigned_devices": devices,
                    "assigned_sample_positions": sample_positions,
                    "status": RequestStatus.FULFILLED.name,
                    "fulfilled_at": datetime.now(),
                }
            },
        )
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
