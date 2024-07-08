"""
Each task process will have a ``LabView`` instance, through which it can request
the lab resources (devices and sample positions).

It can also update the position of a sample in the lab.
"""

import time
from contextlib import contextmanager
from traceback import format_exc
from typing import Any

from bson import ObjectId
from pydantic import root_validator
from pydantic.main import BaseModel

from alab_management.device_manager import DevicesClient
from alab_management.device_view.device import BaseDevice
from alab_management.experiment_view.experiment_view import ExperimentView
from alab_management.logger import DBLogger
from alab_management.resource_manager.resource_requester import ResourceRequester
from alab_management.sample_view.sample import Sample
from alab_management.sample_view.sample_view import SamplePositionRequest, SampleView
from alab_management.task_view.task import BaseTask
from alab_management.task_view.task_enums import TaskPriority, TaskStatus
from alab_management.task_view.task_view import TaskView
from alab_management.user_input import request_user_input, request_user_input_with_note


class DeviceRunningException(Exception):
    """Raise when a task try to release a device that is still running."""


class ResourcesRequest(BaseModel):
    """
    This class is used to validate the resource request. Each request should have a format of
    [DeviceType: List of SamplePositionRequest].

    See Also
    --------
        :py:class:`SamplePositionRequest <alab_management.sample_view.sample_view.SamplePositionRequest>`
    """

    __root__: dict[type[BaseDevice] | None, list[SamplePositionRequest]]  # type: ignore

    @root_validator(pre=True, allow_reuse=True)
    def preprocess(cls, values):
        """Preprocess the request to make sure the request is in the correct format."""
        values = values["__root__"]
        # if the sample position request is string, we will automatically add a number attribute = 1.
        values = {
            k: [
                SamplePositionRequest.from_str(v_) if isinstance(v_, str) else v_
                for v_ in v
            ]
            for k, v in values.items()
        }
        return {"__root__": values}


class LabView:
    """
    LabView is a wrapper over device view and sample view.
    A task can get access to that to request resources, query sample and
    update sample positions.
    """

    def __init__(self, task_id: ObjectId):
        self._task_view = TaskView()
        self.__task_entry = self._task_view.get_task(
            task_id=task_id
        )  # will throw error if task_id does not exist
        self._experiment_view = ExperimentView()
        self._task_id = task_id
        self._sample_view = SampleView()
        self._resource_requester = ResourceRequester(task_id=task_id)
        self._device_client = DevicesClient(task_id=task_id, timeout=None)
        self.logger = DBLogger(task_id=task_id)

        self._priority = TaskPriority.NORMAL.value

    @property
    def task_id(self) -> ObjectId:
        """Get the task id of the current task."""
        return self._task_id

    @contextmanager
    def request_resources(
        self,
        resource_request: dict[type[BaseDevice] | str | None, dict[str, str | int]],
        priority: int | None = None,
        timeout: float | None = None,
    ):
        """
        Request devices and sample positions. This function is a context manager, which should be used in
        a with statement to ensure all the devices are released when the task is done.

        resource_request format is: {device: {position: number, ...}, ...} device can be a name of a specific device
        (str), a type of device, or None. If device is a type, the resource request will look for any available
        device of that type. If device is None, the resource request will look for sample positions that do not
        belong to a device. position is the name of a sample position that should be reserved on the device,
        and number is the number of such positions that should be reserved. If the device is required but no
        positions are required, this can be left as an empty dictionary.

        Examples -------- {TubeFurnace: {"tray": 4}, "arm1": {}} will find the first available TubeFurnace device,
        then reserve 4 sample positions of "{tubefurnacename}/tray/{tray_index}" on that device. It will also find
        the device named "arm1".


        The priority of the request can optionally be specified as a positive integer, which should probably be in
        the range of 0-40. 20 is the default "NORMAL" priority level. Higher number = higher priority. Numbers >= 100
        are reserved for urgent/error correcting requests.
        """
        priority = priority or self.priority

        self._task_view.update_status(
            task_id=self.task_id, status=TaskStatus.REQUESTING_RESOURCES
        )
        result = self._resource_requester.request_resources(
            resource_request=resource_request, timeout=timeout, priority=priority
        )
        request_id = result["request_id"]
        devices = result["devices"]
        sample_positions = result["sample_positions"]
        devices = {
            device_type: self._device_client.create_device_wrapper(device_name)
            for device_type, device_name in devices.items()
        }  # type: ignore
        self._task_view.update_status(task_id=self.task_id, status=TaskStatus.RUNNING)
        yield devices, sample_positions

        self._resource_requester.release_resources(request_id=request_id)

    def _sample_name_to_id(self, sample_name: str) -> ObjectId:
        """
        Get a sample id by name.

        Looks up sample name->id mapping for the experiment `self.task_id` belongs to.
        """
        for sample in self.__task_entry["samples"]:
            if sample["name"] == sample_name:
                return sample["sample_id"]
        raise ValueError(
            f"No sample with name \"{sample_name}\" found for task \"{self.__task_entry['type']}\""
        )

    def get_sample(self, sample: ObjectId | str) -> Sample:
        """
        Get a sample by either an ObjectId corresponding to sample_id, or as a string corresponding to the sample's
        name within the experiment., see also :py:meth:`get_sample
        <alab_management.sample_view.sample_view.SampleView.get_sample>`.
        """
        if isinstance(sample, str):
            sample_id = self._sample_name_to_id(sample)
        elif isinstance(sample, ObjectId):
            sample_id = sample
        else:
            raise TypeError("sample must be a sample name (str) or id (ObjectId)")
        return self._sample_view.get_sample(sample_id=sample_id)

    def move_sample(self, sample: ObjectId | str, position: str | None):
        """
        Move a sample to a new position. `sample` can be given as either an ObjectId corresponding to sample_id,
        or as a string corresponding to the sample's name within the experiment.

        See Also
        --------
        :py:meth:`move_sample <alab_management.sample_view.sample_view.SampleView.move_sample>`
        """
        # check if this sample position is locked by current task
        if (
            position is not None
            and self._sample_view.get_sample_position_status(position)[1]
            != self._task_id
        ):
            # Wait a few seconds for the sample position to be locked in case it is not
            # locked by the current task yet.
            for _ in range(5):
                time.sleep(1)
                if (
                    self._sample_view.get_sample_position_status(position)[1]
                    == self._task_id
                ):
                    break
            if (
                self._sample_view.get_sample_position_status(position)[1]
                != self._task_id
            ):
                raise ValueError(
                    f"Cannot move sample to the new sample position ({position}) without locking it."
                )

        # check if this sample is owned by current task
        sample_entry = self.get_sample(sample=sample)
        if sample_entry.task_id != self._task_id:
            raise ValueError("Cannot move a sample that does not belong to this task.")
        self._sample_view.move_sample(
            sample_id=sample_entry.sample_id, position=position
        )

    def get_locked_sample_positions(self) -> list[str]:
        """Get a list of sample positions that are occupied by this task."""
        return self._sample_view.get_sample_positions_by_task(task_id=self._task_id)

    def get_sample_position_parent_device(self, position: str) -> str | None:
        """Get the name of the device that owns the sample position."""
        return self._sample_view.get_sample_position_parent_device(position=position)

    def update_sample_metadata(self, sample: ObjectId | str, metadata: dict[str, Any]):
        """
        Update the metadata of a sample. `sample` can be given as either an ObjectId corresponding to sample_id,
        or as a string corresponding to the sample's name within the experiment.

        See Also
        --------
        :py:meth:`update_sample_metadata <alab_management.sample_view.sample_view.SampleView.update_sample_metadata>`
        """
        if isinstance(sample, str):
            sample_id = self._sample_name_to_id(sample)
        elif isinstance(sample, ObjectId):
            sample_id = sample
        else:
            raise TypeError("sample must be a sample name (str) or id (ObjectId)")

        return self._sample_view.update_sample_metadata(
            sample_id=sample_id, metadata=metadata
        )

    def run_subtask(
        self, task: type[BaseTask], samples: list[ObjectId | str], **kwargs
    ):
        """Run a task as a subtask within the task. basically fills in task_id and lab_view for you.
            this command blocks until the subtask is completed.

        Args:
        task (Type[BaseTask]): The type/class of the Task to run.
        samples (List[Union[ObjectId, str]]): List of sample IDs or names.
        **kwargs: will be passed to the Task method via the parameters entry in the task collection.
        """
        if not issubclass(task, BaseTask):
            raise TypeError("task must be a subclass of BaseTask!")
        # TODO maybe check if task is in task_registry? for future if tasks are somehow checked when adding to registry

        # task_id and lab_view kwargs forced to match that of current LabView instance
        kwargs.pop("task_id", None)
        kwargs.pop("lab_view", None)
        task_id = self._task_id
        lab_view = self

        subtask_id = self._task_view.create_subtask(
            task_id=task_id,
            subtask_type=task.__name__,
            samples=samples,
            parameters=kwargs,
        )
        try:
            subtask: BaseTask = task(
                simulation=False,
                task_id=task_id,
                lab_view=lab_view,
                samples=samples,
                **kwargs,
            )
        except Exception as exc:
            self._task_view.update_subtask_status(
                task_id=task_id, subtask_id=subtask_id, status=TaskStatus.ERROR
            )
            self._task_view.update_subtask_result(
                task_id=task_id, subtask_id=subtask_id, result=str(exc)
            )
            raise Exception(
                "Failed to create subtask of type {} within task {} of type {}".format(
                    task,
                    task_id,
                    self._task_view.get_task(task_id=task_id, encode=True)["type"],
                )
            ) from exc
        self.logger.system_log(
            level="INFO",
            log_data={
                "logged_by": "TaskActor",
                "type": "SubTaskStart",
                "task_id": task_id,
                "subtask_type": task.__name__,
            },
        )
        try:
            self._task_view.update_subtask_status(
                task_id=task_id, subtask_id=subtask_id, status=TaskStatus.RUNNING
            )
            result = subtask.run()  # block until completion
        except Exception as exception:
            self._task_view.update_subtask_status(
                task_id=task_id, subtask_id=subtask_id, status=TaskStatus.ERROR
            )
            self._task_view.update_subtask_result(
                task_id=task_id, subtask_id=subtask_id, result=str(exception)
            )
            self.logger.system_log(
                level="ERROR",
                log_data={
                    "logged_by": "TaskActor",
                    "type": "SubTaskEnd",
                    "task_id": task_id,
                    "subtask_type": task.__name__,
                    "status": "ERROR",
                    "traceback": format_exc(),
                },
            )
            raise
        else:
            self._task_view.update_subtask_status(
                task_id=task_id, subtask_id=subtask_id, status=TaskStatus.COMPLETED
            )
            self._task_view.update_subtask_result(
                task_id=task_id, subtask_id=subtask_id, result=result
            )
            self.logger.system_log(
                level="INFO",
                log_data={
                    "logged_by": "TaskActor",
                    "type": "SubTaskEnd",
                    "task_id": task_id,
                    "subtask_type": task.__name__,
                    "status": "COMPLETED",
                },
            )
        return result

    def request_user_input(self, prompt: str, options: list[str]) -> str:
        """Request user input from the user. This function will block until the user inputs something. Returns the
        value returned by the user.
        """
        return request_user_input(task_id=self.task_id, prompt=prompt, options=options)

    def request_user_input_with_note(
        self, prompt: str, options: list[str]
    ) -> tuple[str, str]:
        """Request user input from the user. This function will block until the user inputs something. Returns the
        value returned by the user and the note.
        """
        return request_user_input_with_note(
            task_id=self.task_id, prompt=prompt, options=options
        )

    @property
    def priority(self) -> int:
        """Get the priority of the task."""
        return self._priority

    @priority.setter
    def priority(self, priority: int):
        if isinstance(priority, TaskPriority):
            priority = priority.value
        self._priority = priority

    def update_result(self, name: str, value: Any):
        """
        Update a result of the task. This result will be saved in the task collection under `results.name` and can be
        retrieved later.

        Args: name (str): name of the result (ie "diffraction pattern"). This will be used as the key in the results
        dictionary. value (Any): value of the result. This can be a numpy array, a set, or any other
        bson-serializable object (most standard Python types).
        """
        self._task_view.update_result(task_id=self.task_id, name=name, value=value)

    def request_cleanup(self):
        """Request cleanup of the task. This function will block until the task is cleaned up."""
        all_reserved_sample_positions = self._sample_view.get_sample_positions_by_task(
            self.task_id
        )

        all_samples = self.__task_entry["samples"]
        all_positions_with_samples = [
            self._sample_view.get_sample(sample_entry["sample_id"]).position
            for sample_entry in all_samples
        ]

        all_positions_with_samples = [
            each for each in all_positions_with_samples if each
        ]

        self.request_user_input(
            prompt="A unrecoverable error has occurred.\n"
            f"(1) remove samples on {', '.join(all_positions_with_samples)}\n"
            f"(2) remove all other consumables on {', '.join(all_reserved_sample_positions)}\n"
            f"The error information is {format_exc()}",
            options=["OK"],
        )

        # move the samples out of the lab
        for sample in all_samples:
            self.move_sample(sample=sample["sample_id"], position=None)

        # release all the resource that has not been fulfilled
        self._resource_requester.release_all_resources()
