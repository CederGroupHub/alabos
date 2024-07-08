"""Define the base class of task, which will be used for defining more tasks."""

import inspect
from abc import ABC, abstractmethod
from inspect import getfullargspec
from typing import TYPE_CHECKING, Any, Optional

from bson.objectid import ObjectId
from pydantic import BaseModel

from alab_management.builders.experimentbuilder import ExperimentBuilder
from alab_management.builders.samplebuilder import SampleBuilder
from alab_management.task_view.task_enums import TaskPriority

if TYPE_CHECKING:
    from alab_management.device_view.device import BaseDevice
    from alab_management.lab_view import LabView


class ResultPointer:
    """A reference to a result generated by a task. This result can then be imported by another task."""

    def __init__(self, task_id: ObjectId, key: str):
        self.task_id = task_id
        self.key = key

    def to_json(self):
        """Convert this ResultPointer to a JSON-serializable dictionary."""
        return {
            "type": "ResultPointer",
            "task_id": str(self.task_id),
            "key": self.key,
        }

    @classmethod
    def from_json(cls, json: dict[str, Any]):
        """Create a ResultPointer from a JSON-serializable dictionary."""
        if json["type"] != "ResultPointer":
            raise ValueError("JSON does not encode a ResultPointer!")
        return cls(task_id=ObjectId(json["task_id"]), key=json["key"])


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
        simulation: bool = True,
        *args,
        **kwargs,
    ):
        """
        Args:
            task_id: the identifier of task
            lab_view: a lab_view corresponding to the task_id
            samples: a list of sample_id's corresponding to samples involvend in the task.

        Here is an example about how to define a custom task

        .. code-block:: python

          def __init__(self, sample_1: ObjectId, sample_2: Optional[ObjectId],
                       sample_3: Optional[ObjectId], sample_4: Optional[ObjectId],
                        setpoints: List[Tuple[float, float]], *args, **kwargs):
              super(Heating, self).__init__(*args, **kwargs)
              self.setpoints = setpoints
              self.samples = [sample_1, sample_2, sample_3, sample_4]
        """
        self.__simulation = simulation

        self.__samples = samples or []
        if self.is_simulation:
            task_id = task_id or ObjectId()  # if None, generate an ID now
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
                    "BaseTask was instantiated with simulation mode off -- task_id, "
                    "lab_view, and samples must all be provided!"
                )
            self.task_id = task_id
            self.lab_view = lab_view
            self.logger = self.lab_view.logger
            self.priority = priority
            self.lab_view.priority = priority
            # if not self.validate(): #TODO: implement this
            #     raise ValueError("Task validation failed!")

    @property
    def is_simulation(self) -> bool:
        """Returns True if this task is a simulation, False if it is a live task."""
        return self.__simulation

    @property
    def samples(self) -> list[str]:
        """Returns the list of samples associated with this task."""
        return self.__samples

    @property
    def priority(self) -> int:
        """Returns the priority of this task."""
        if self.is_simulation:
            return 0
        return self.lab_view._resource_requester.priority

    @property
    @abstractmethod
    def result_specification(self) -> BaseModel:
        """Returns a dictionary describing the results to be generated by this task.

        Raises
        ------
            NotImplementedError: The subclass must implement this method.

        Returns
        -------
            BaseModel: A Pydantic model describing the results to be generated by this task.
        """
        raise NotImplementedError(
            "The .result_specification method must be implemented by a subclass of BaseTask."
        )

    @priority.setter
    def priority(self, value: int | TaskPriority):
        if value < 0:
            raise ValueError("Priority should be a positive integer")
        if not self.__simulation:
            self.lab_view._resource_requester.priority = int(value)

    def set_message(self, message: str):
        """Sets the task message to be displayed on the dashboard."""
        self._message = message
        if not self.__simulation:
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
        """
        # raise NotImplementedError(
        #     "The .validate method must be implemented by a subclass of BaseTask"
        # )
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

    def add_to(
        self,
        samples: SampleBuilder | list[SampleBuilder],
    ):
        """Used to add basetask to a SampleBuilder's tasklist during Experiment construction.

        Args: samples (Union[SampleBuilder, List[SampleBuilder]]): One or more SampleBuilder's which will have this
        task appended to their tasklists.
        """
        if not self.__simulation:
            raise RuntimeError(
                "Cannot add a live BaseTask instance to a SampleBuilder. BaseTask must be instantiated with "
                "`simulation=True` to enable this method."
            )
        if isinstance(samples, SampleBuilder):
            samples = [samples]

        experiment: ExperimentBuilder = samples[0].experiment
        task_id = str(ObjectId())
        experiment.add_task(
            task_id=task_id,
            task_name=self.__class__.__name__,
            task_kwargs=self.subclass_kwargs,
            samples=samples,
        )
        for sample in samples:
            sample.add_task(task_id=task_id)


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
