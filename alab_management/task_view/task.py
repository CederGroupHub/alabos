"""Define the base class of task, which will be used for defining more tasks."""

import inspect
import time
from abc import ABC, abstractmethod
from inspect import getfullargspec
from pathlib import Path
from typing import TYPE_CHECKING, Any, Optional

import gridfs
from bson.objectid import ObjectId
from pydantic import BaseModel, ConfigDict, Field, model_validator

from alab_management.builders.samplebuilder import SampleBuilder
from alab_management.config import AlabOSConfig
from alab_management.task_view.task_enums import TaskPriority
from alab_management.utils.data_objects import get_db

if TYPE_CHECKING:
    from alab_management.builders.experimentbuilder import ExperimentBuilder
    from alab_management.device_view.device import BaseDevice
    from alab_management.lab_view import LabView


_UNSET = object()


class LargeResult(BaseModel):
    """
    A Pydantic model for a large result (file >16 MB).
    Stored in either gridFS or other filesystems (Cloud AWS S3, etc.).
    """

    # to avoid import AlabOSConfig at the top level
    storage_type: str = Field(
        default_factory=lambda: AlabOSConfig()["large_result_storage"][
            "default_storage_type"
        ]
    )
    # The path to the local file, used for uploading
    local_path: str | Path | None = None
    # The identifier of the file in the storage system, can be a path or a key (e.g., gridfs id)
    # Obtained after storing the file, used for retrieving
    identifier: str | ObjectId | None = None
    # alternative to local path, used for uploading, local path has higher priority
    file_like_data: Any | None = None

    model_config = ConfigDict(arbitrary_types_allowed=True)

    # if file_like_data is provided check if it has .read() method
    @model_validator(mode="before")
    def check_file_like_data(cls, values):
        """Check if file_like_data has a .read() method."""
        file_like_data = values.get("file_like_data")
        if file_like_data is not None and not hasattr(file_like_data, "read"):
            raise ValueError("file_like_data must have a .read() method")
        return values

    @classmethod
    def from_local_file(cls, local_path: str | Path, storage_type: str = _UNSET):
        """
        Create a LargeResult object from a local file and store it.
        If file is failed to be stored, will raise a ValueError.

        Args:
            local_path: the path to the local file
            storage_type: the storage type, default to the default storage type in the config

        Returns
        -------
            LargeResult: the LargeResult object

        """
        if storage_type is _UNSET:
            storage_type = AlabOSConfig()["large_result_storage"][
                "default_storage_type"
            ]
        large_file = cls(local_path=local_path, storage_type=storage_type)
        large_file.store()
        return large_file

    @classmethod
    def from_file_like_data(cls, file_like_data: Any, storage_type: str = _UNSET):
        """
        Create a LargeResult object from a file-like object.
        File-like object must have a .read() method.
        If file is failed to be stored, will raise a ValueError.

        Args:
            file_like_data: the file-like data
            storage_type: the storage type, default to the default storage type in the config

        Returns
        -------
            LargeResult: the LargeResult object
        """
        if storage_type is _UNSET:
            storage_type = AlabOSConfig()["large_result_storage"][
                "default_storage_type"
            ]
        large_result = cls(file_like_data=file_like_data, storage_type=storage_type)
        large_result.store()
        return large_result

    def store(self):
        """
        Store the large result in the storage system.
        This method should block until the result is confirmed to be stored.
        This method should have a timeout regardless of the storage system to not block indefinitely.
        """
        if self.storage_type == "gridfs":
            db = get_db()
            fs = gridfs.GridFS(db)
            if self.local_path:
                with open(self.local_path, "rb") as file:
                    file_id = fs.put(file)
            elif self.file_like_data:
                file_id = fs.put(self.file_like_data)
            else:
                raise ValueError(
                    "Either local_path or serializable_data must be provided for storing in gridfs."
                )
            self.identifier = file_id
            # check if the file is stored, wait until it is stored for maximum 10 seconds
            for _ in range(10):
                if fs.exists(file_id):
                    return
                time.sleep(1)
            raise ValueError(f"File with identifier {file_id} failed to be stored.")
        else:
            raise ValueError("Only gridfs storage is supported for now.")

    def retrieve(self):
        """Retrieve the large result from the storage system."""
        if self.storage_type == "gridfs":
            if self.identifier is None:
                raise ValueError(
                    "Identifier is not provided for retrieving from gridfs."
                )
            db = get_db()
            fs = gridfs.GridFS(db)
            if fs.get(self.identifier) is None:
                raise ValueError(
                    f"File with identifier {self.identifier} does not exist."
                )
            return fs.get(self.identifier).read()
        else:
            raise ValueError("Only gridfs storage is supported for now.")

    def check_if_stored(self):
        """Check if the large result is stored in the storage system."""
        if self.storage_type == "gridfs":
            if self.identifier is None:
                return False
            db = get_db()
            fs = gridfs.GridFS(db)
            return fs.exists(self.identifier)
        else:
            raise ValueError("Only gridfs storage is supported for now.")


class BaseTask(ABC):
    """
    The abstract class of task.

    All the tasks should inherit from this class.
    """

    def __init__(
        self,
        samples: list[str | ObjectId] | None = None,
        task_id: ObjectId | None = None,
        lab_view: Optional["LabView"] = None,
        priority: TaskPriority | int | None = TaskPriority.NORMAL,
        _offline_mode: bool = True,
        *args,
        **kwargs,
    ):
        """
        Args:
            task_id: the identifier of task
            lab_view: a lab_view corresponding to the task_id
            samples: a list of sample_id's corresponding to samples involvend in the task.
            _offline_mode: whether the task is run in offline mode or not. It is in offline mode when you
              are trying to build an experiment out of it or get the task result.

        Here is an example about how to define a custom task

        .. code-block:: python

          def __init__(self, sample_1: ObjectId, sample_2: Optional[ObjectId],
                       sample_3: Optional[ObjectId], sample_4: Optional[ObjectId],
                        setpoints: List[Tuple[float, float]], *args, **kwargs):
              super(Heating, self).__init__(*args, **kwargs)
              self.setpoints = setpoints
              self.samples = [sample_1, sample_2, sample_3, sample_4]
        """
        self.__offline = _offline_mode
        self._is_taskid_generated = (
            False  # whether the task_id is generated using ObjectId() here or not
        )

        self.__samples = samples or []
        if self.is_offline:
            if task_id is None:  # if task_id is not provided, generate one
                self._is_taskid_generated = True
                task_id = ObjectId()
            self.task_id = task_id
            current_frame = inspect.currentframe()
            outer_frames = inspect.getouterframes(current_frame)
            subclass_init_frame = outer_frames[1].frame
            self.subclass_kwargs = {
                key: val
                for key, val in inspect.getargvalues(subclass_init_frame).locals.items()
                if key not in ["self", "args", "kwargs", "__class__"]
            }
        else:
            if (task_id is None) or (lab_view is None) or (samples is None):
                raise ValueError(
                    "BaseTask was instantiated with offline mode off -- task_id, "
                    "lab_view, and samples must all be provided!"
                )
            self.task_id = task_id
            self.lab_view = lab_view
            self.logger = self.lab_view.logger
            self.priority = priority
            self.lab_view.priority = priority

    @property
    def is_offline(self) -> bool:
        """Returns True if this task is in offline, False if it is a live task."""
        return self.__offline

    @property
    def samples(self) -> list[str]:
        """Returns the list of samples associated with this task."""
        return self.__samples

    @property
    def priority(self) -> int:
        """Returns the priority of this task."""
        if self.is_offline:
            return 0
        return self.lab_view._resource_requester.priority

    @property
    def result_specification(self) -> type[BaseModel] | None:
        """
        Returns a pydantic model describing the results to be generated by this task.
        If specified, this model will be used by task_actor to validate the results after the task is completed.
        If any error occurs, a warning will be printed.
        If there is a LargeResult in the result, it will ensured to be stored in the database.

        Raises
        ------
            NotImplementedError: The subclass must implement this method.

        Returns
        -------
            BaseModel: A Pydantic model type describing the results to be generated by this task.
        """
        return None

    @priority.setter
    def priority(self, value: int | TaskPriority):
        if value < 0:
            raise ValueError("Priority should be a positive integer")
        if not self.__offline:
            self.lab_view._resource_requester.priority = int(value)

    def set_message(self, message: str):
        """Sets the task message to be displayed on the dashboard."""
        self._message = message
        if not self.__offline:
            self.lab_view._task_view.set_message(task_id=self.task_id, message=message)

    def get_message(self):
        """Gets the task message to be displayed on the dashboard."""
        return self._message

    def validate(self) -> bool:
        """
        Validate the task.

        This function will be called before the task is executed.
        Should return False if the task has values that make it impossible to execute.
        For example, a ``Heating`` subclass of `BaseTask` might return False if the
        set temperature is too high for the furnace.

        By default, this function returns True unless it is overridden by a subclass.
        """
        return True

    @abstractmethod
    def run(self):
        """
        Run the task. In this function, you can request lab resources from lab manager and log data to database
        with logger.

        ``request_resources`` will not return until all the requested resources are available. So the task will
        pend until it gets the requested resources, which prevent the conflict in the resource allocation.

        When a device get the requested device and sample positions, it also takes over the ownership of these
        resources, i.e., other task cannot use the device or request the sample positions this task has requested.

        We use a context manager to manage the ownership of the resources. when a task is completed, all the devices
        and sample positions will be released automatically.

        Here is an example about how to define the task

        .. code-block:: python

          # request devices and sample positions from lab manager. The `$` represents
          # the name of assigned devices in the sample positions we try to request,
          # 4 is the number of sample positions.
          with self.lab_view.request_resources({Furnace: [("$.inside", 4)]}) as devices_and_positions:
              devices, sample_positions = devices_and_positions
              furnace = devices[Furnace]
              inside_furnace = sample_positions[Furnace]["$.inside"]

              for sample in self.samples:
                  # in a task, we can call other tasks, which will share the same
                  # task id, requested devices and sample positions.
                  moving_task = Moving(sample=sample,
                                       task_id=self.task_id,
                                       dest=inside_furnace[0],
                                       lab_view=self.lab_view,
                                       logger=self.logger)
                  moving_task.run()

              # send command to device
              furnace.run_program(self.setpoints)

              while furnace.is_running():
                  # log the device data, which is current temperature of the furnace
                  self.logger.log_device_signal({
                      "device": furnace.name,
                      "temperature": furnace.get_temperature(),
                  })

        """
        raise NotImplementedError(
            "The .run method must be implemented by the subclass of BaseTask."
        )

    def run_subtask(
        self,
        task: type["BaseTask"],
        samples: list[str] | str | None = None,
        **kwargs,
    ):
        """Run a subtask of this current task. Returns the result, if any, of the subtask."""
        samples = samples or self.samples
        if isinstance(samples, str):
            samples = [samples]
        return self.lab_view.run_subtask(task=task, samples=samples, **kwargs)

    @classmethod
    def from_kwargs(
        cls, samples: list[str | ObjectId], task_id: ObjectId, **subclass_kwargs
    ) -> "BaseTask":
        """
        Used to create a new task object from the provided arguments.

        This is used in the `add_to` and `ExperimentBuilder.add_task` method to
        create a new task object and validate it before adding it to an experiment
        or sample builder.
        """
        task_obj = cls(
            samples=samples,
            task_id=task_id,
            offline_mode=True,
            **subclass_kwargs,
        )
        return task_obj

    def add_to(
        self,
        samples: SampleBuilder | list[SampleBuilder],
    ):
        """Used to add basetask to a SampleBuilder's tasklist during Experiment construction.

        Args: samples (Union[SampleBuilder, List[SampleBuilder]]): One or more SampleBuilder's which will have this
        task appended to their tasklists.
        """
        if not self.__offline:
            raise RuntimeError(
                "Cannot add a live BaseTask instance to a SampleBuilder. BaseTask must be instantiated with "
                "`offline_mode=True` to enable this method."
            )

        if isinstance(samples, SampleBuilder):
            samples = [samples]

        experiment: ExperimentBuilder = samples[0].experiment
        task_id = self.task_id

        task_obj = self.__class__.from_kwargs(
            samples=[sample.name for sample in samples],
            task_id=ObjectId(task_id),
            **self.subclass_kwargs,
        )
        if not task_obj.validate():
            raise ValueError(
                "Task input validation failed!"
                + (
                    f"\nError message: {task_obj.get_message()}"
                    if task_obj.get_message()
                    else ""
                )
            )

        experiment.add_task(
            task_id=str(task_id),
            task_name=self.__class__.__name__,
            task_kwargs=self.subclass_kwargs,
            samples=samples,
        )
        for sample in samples:
            sample.add_task(task_id=str(task_id))


_task_registry: dict[str, type[BaseTask]] = {}

SUPPORTED_SAMPLE_POSITIONS_TYPE = dict[type["BaseDevice"] | str | None, str | list[str]]
_reroute_task_registry: list[
    dict[str, type[BaseTask] | SUPPORTED_SAMPLE_POSITIONS_TYPE]
] = []


def add_task(task: type[BaseTask]):
    """Register a task."""
    if task.__name__ in _task_registry:
        raise KeyError(f"Duplicated operation name {task.__name__}")
    _task_registry[task.__name__] = task


def get_all_tasks() -> dict[str, type[BaseTask]]:
    """Get all the tasks in the registry."""
    return _task_registry.copy()


def get_task_by_name(name: str) -> type[BaseTask]:
    """Get a task by name."""
    return _task_registry[name]


def add_reroute_task(
    supported_sample_positions: SUPPORTED_SAMPLE_POSITIONS_TYPE,
    task: type[BaseTask],
    **kwargs,
):
    """Register a reroute task."""
    if task.__name__ not in _task_registry:
        raise KeyError(
            f"Task {task.__name__} is not registered! Register with `add_task` before registering as a reroute task."
        )
    if "sample" not in getfullargspec(task).args:
        raise ValueError(
            f"Task {task.__name__} does not have `sample` as a parameter! "
            "Reroute tasks must accept a `sample` parameter that specifies the name or sample_id of the sample to be "
            "rerouted"
        )
    _reroute_task_registry.append(
        {
            "supported_sample_positions": supported_sample_positions,
            "task": task,
            "kwargs": kwargs,
        }
    )
