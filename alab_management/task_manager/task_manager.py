"""
TaskLauncher is the core module of the system,
which actually executes the tasks.
"""

import time
from datetime import datetime
from functools import partial
from math import inf
from threading import Thread
from typing import Any, cast

import dill
import networkx as nx
from bson import ObjectId
from dramatiq_abort import abort

from alab_management.device_view import BaseDevice, get_all_devices
from alab_management.device_view.device_view import DeviceView
from alab_management.lab_view import LabView
from alab_management.logger import DBLogger, LoggingLevel
from alab_management.sample_view.sample import SamplePosition
from alab_management.sample_view.sample_view import SamplePositionRequest, SampleView
from alab_management.task_actor import run_task
from alab_management.task_view import TaskPriority, TaskView
from alab_management.task_view.task import BaseTask
from alab_management.task_view.task_enums import TaskStatus
from alab_management.utils.data_objects import get_collection
from alab_management.utils.module_ops import load_definition

from .enums import _EXTRA_REQUEST
from .resource_requester import (
    RequestMixin,
    RequestStatus,
)


def parse_reroute_tasks() -> dict[str, type[BaseTask]]:
    """
    Takes the reroute task registry and expands the supported sample positions (which is given in format similar to
    resource requests) to the individual sample positions.

    Raises
    ------
        ValueError: if the supported_sample_positions is not provided in the correct format.

    Returns
    -------
        _type_: _description_
    """
    from alab_management.sample_view import SampleView
    from alab_management.task_view.task import _reroute_task_registry

    # return []

    load_definition()

    routes: dict[str, BaseTask] = {}  # sample_position: Task
    sample_view = SampleView()

    for reroute in _reroute_task_registry:
        route_task = partial(reroute["task"], **reroute["kwargs"])
        supported_sample_positions = reroute["supported_sample_positions"]

        for device_identifier, positions in supported_sample_positions.items():
            if device_identifier is None:
                devices = [None]
            elif isinstance(device_identifier, str):
                devices = [device_identifier]  # name of particular device
            elif issubclass(device_identifier, BaseDevice):
                devices = [
                    name
                    for name, device_instance in get_all_devices().items()
                    if isinstance(device_instance, device_identifier)
                ]  # all devices of this type
            else:
                raise ValueError(
                    "device must be a name of a specific device, a class of type BaseDevice, or None"
                )

            if isinstance(positions, str):
                positions = [positions]  # noqa: PLW2901
            for device in devices:
                for position in positions:
                    if device is None and position == "":
                        raise ValueError(
                            'Cannot have device=None and position="" -- this would return every sample_position!'
                        )
                    if device is not None:
                        position = f"{device}{SamplePosition.SEPARATOR}{position}"  # noqa: PLW2901
                    for found_position in sample_view._sample_positions_collection.find(
                        {"name": {"$regex": position}}
                    ):  # DB_ACCESS_OUTSIDE_VIEW
                        routes[found_position["name"]] = route_task
    return routes


_reroute_registry = parse_reroute_tasks()


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
        self.__reroute_in_progress = False

        self.__skip_checking_task_id = False

        self.logger = DBLogger(task_id=None)
        super().__init__()
        time.sleep(1)  # allow some time for other modules to launch

    def run(self):
        """Start the loop."""
        while True:
            self._loop()
            time.sleep(2)

    def _loop(self):
        self.submit_ready_tasks()
        self.handle_released_resources()
        self.handle_tasks_to_be_cancelled()
        self.handle_requested_resources()

        if not self.__reroute_in_progress:
            self.handle_request_cycles()

    def _clean_up_tasks_from_previous_runs(self):
        """Cleans up incomplete tasks that exist from the last time the taskmanager was running. Note that this will
        block the task queue until all samples in these tasks have been removed from the physical lab (confirmed via
        user requests on the dashboard).

        This typically occurs if the taskmanager was exited using SIGTERM (ctrl-c), in which case some tasks may
        still be in the RUNNING or CANCELLING state. These will be set to CANCELLED now.
        """
        statuses_to_cancel = [
            TaskStatus.RUNNING,
            TaskStatus.CANCELLING,
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
            result = run_task.send(task_id_str=str(task_entry["task_id"]))
            message_id = result.message_id
            self.task_view.set_task_actor_id(
                task_id=task_entry["task_id"], message_id=message_id
            )

    def handle_tasks_to_be_cancelled(self):
        """
        Check if there are any tasks that are in CANCELLING status. If so, cancel them.

        This is done by sending a dramatiq abort message to the task actor process. The task actor process will
        update the status from CANCELLING to CANCELLED.
        """
        tasks_to_be_cancelled = self.task_view.get_tasks_by_status(
            status=TaskStatus.CANCELLING
        )

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
            message_id = task_entry.get("task_actor_id", None)
            if message_id is not None:
                abort(message_id=message_id)
                # updating the status from CANCELLING to CANCELLED will be executed in task actor process
            else:
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

    def handle_request_cycles(self):
        """Check for request cycles (gridlocks where a set of tasks require sample_positions occupied by one
        another.). We attempt to resolve these cycles by moving a sample out of the way by a reroute_task defined in
        the alab configuration. This will move samples to free up the blocked task of highest priority. If this alone
        does not resolve the cycle, we will try again on the next call to this method.
        """
        positions_to_reroute, taskid_to_reroute = self._check_for_request_cycle()
        if len(positions_to_reroute) > 0:
            thread = Thread(
                target=self._reroute_to_fix_request_cycle,
                kwargs={
                    "task_id": taskid_to_reroute,
                    "sample_positions": positions_to_reroute,
                },
            )
            thread.daemon = False
            thread.start()

    def _handle_requested_resources(self, request_entry: dict[str, Any]):
        try:
            resource_request = request_entry["request"]
            task_id = request_entry["task_id"]

            if not self.__skip_checking_task_id:
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
            # wait until the parsed_sample_positions_request is updated in the database
            while self.get_request(request_entry["_id"], projection=["parsed_sample_positions_request"])["parsed_sample_positions_request"] is None:
                time.sleep(0.5)

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
            while self.get_request(request_entry["_id"], projection=["status"])[
                "status"].name != "ERROR":
                time.sleep(0.5)
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
        # Wait until the status of the request is updated in the database
        while self.get_request(request_entry["_id"], projection=["status"])[
            "status"] != "FULFILLED":
            time.sleep(0.5)
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

    def _check_for_request_cycle(self):
        """Check if there is a cycle in the request graph. (ie tasks occupy sample positions required by one another,
        no requests can be fulfilled). If found, use a reroute task to fix the cycle. This function will only trigger
        if a reroute task has been defined using `add_reroute`.
        """
        tasks = self.task_view.get_tasks_by_status(TaskStatus.REQUESTING_RESOURCES)

        if len(tasks) < 2:
            return [], None  # no cycle to fix

        # get occupied and requested positions per task that is currently requesting resources
        occupied_by_task = {}
        requested_by_task = {}
        task_priority = {}
        task_ids_to_consider = []
        for t in tasks:
            request = self._request_collection.find_one(
                {"task_id": t["task_id"], "status": RequestStatus.PENDING.name}
            )  # DB_ACCESS_OUTSIDE_VIEW
            if request is None:
                # race condition. task must have had resource request fulfilled between getting task and
                # request entries.
                continue
            if "parsed_sample_positions_request" not in request:
                # slight delay between setting TaskStatus.REQUESTING_RESOURCES and generating
                # parsed_sample_positions_request. can catch these on the next call if necessary.
                continue
            task_ids_to_consider.append(t["task_id"])
            occupied = occupied_by_task[t["task_id"]] = []
            blocked = requested_by_task[t["task_id"]] = []
            task_priority[t["task_id"]] = request["priority"]
            for s in t["samples"]:
                occupied.append(self.sample_view.get_sample(s["sample_id"]).position)
            for r in request["parsed_sample_positions_request"]:
                if (
                    len(
                        self.sample_view.get_available_sample_position(
                            task_id=t["task_id"], position_prefix=r["prefix"]
                        )
                    )
                    < r["number"]
                ):
                    blocked.append(
                        r["prefix"]
                    )  # we dont have enough available positions for this request

        # construct a directed graph where nodes are task_id's, and edges indicate that the tail node is blocked by
        # the head node (ie the tail task is requesting a sample_position occupied by the head task)
        edges = []
        for i, t0 in enumerate(task_ids_to_consider):
            for j, t1 in enumerate(task_ids_to_consider):
                if i == j:
                    continue
                if any(
                    occupied in requested_by_task[t0]
                    for occupied in occupied_by_task[t1]
                ):
                    edges.append((t0, t1))

        if len(edges) < 2:
            return [], None  # no cycle without at least two edges
        g = nx.DiGraph(edges)
        try:
            cycle = nx.find_cycle(
                g
            )  # a cycle indicates a set of tasks that are blocking one another
        except nx.NetworkXNoCycle:
            return [], None  # no cycle to fix

        # get the highest priority task in the cycle. We will unblock this task.
        highest_priority = -inf
        for _blocking_taskid, _occupying_taskid in cycle:
            priority = task_priority[_blocking_taskid]
            if priority > highest_priority:
                highest_priority = priority
                occupying_taskid = _occupying_taskid
                blocked = requested_by_task[_blocking_taskid]
                occupied = occupied_by_task[_occupying_taskid]
        positions_to_vacate = [p for p in occupied if p in blocked]

        return positions_to_vacate, occupying_taskid

    def _reroute_to_fix_request_cycle(
        self,
        task_id: ObjectId,
        sample_positions: list[str],
    ):
        from alab_management.lab_view import LabView

        """
        Runs rerouting tasks (as specified by add_reroute_task) to vacate sample_positions to resolve a request cycle.

        task_id: the task_id of the blocking task that will be rerouted sample_positions: sample_positions occupied
        by the blocking task which will be moved by the appropriate reroute task."""

        self.__reroute_in_progress = True
        lab_view = LabView(task_id=task_id)
        for fix_position in sample_positions:
            if fix_position not in _reroute_registry:
                raise ValueError(
                    f'No reroute task defined to move sample out from sample_position "{fix_position}". Please add a '
                    f"reroute task using `add_reroute`"
                )
            reroute_Task: BaseTask = _reroute_registry[fix_position]

            sample_to_move = self.sample_view._sample_collection.find_one(
                {"position": fix_position}
            )  # DB_ACCESS_OUTSIDE_VIEW
            lab_view.logger.system_log(
                level=LoggingLevel.INFO,
                log_data={
                    "logged_by": "TaskManager",
                    "type": "Reroute",
                    "reroute_task": {
                        "task_type": reroute_Task.func.__name__,
                        "kwargs": reroute_Task.keywords,
                    },
                    "reroute_target": {
                        "task_id": task_id,
                        "sample_id": sample_to_move["_id"],
                        "sample_position": fix_position,
                    },
                },
            )
            reroute_Task(
                task_id=task_id,
                lab_view=lab_view,
                priority=TaskPriority.HIGH,
                sample=sample_to_move["_id"],
            ).run()
        self.__reroute_in_progress = False
