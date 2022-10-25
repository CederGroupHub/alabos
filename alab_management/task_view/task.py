"""
Define the base class of task, which will be used for defining more tasks.
"""
from abc import ABC, abstractmethod
from typing import Dict, List, Type, TYPE_CHECKING, Optional, Union
from bson.objectid import ObjectId
from alab_management.task_view.task_enums import TaskPriority
from alab_management.device_view.device import BaseDevice
from inspect import getfullargspec

if TYPE_CHECKING:
    from alab_management.lab_view import LabView


class BaseTask(ABC):
    """
    The abstract class of task.

    All the tasks should inherit from this class.
    """

    def __init__(
        self,
        task_id: ObjectId,
        lab_view: "LabView",
        # samples: List[ObjectId],
        priority: Optional[Union[TaskPriority, int]] = TaskPriority.NORMAL,
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
        self.task_id = task_id
        self.child_task_num: int = 0
        self.lab_view = lab_view
        self.logger = self.lab_view.logger
        self.priority = priority
        # self.samples = samples

    @property
    def priority(self) -> int:
        return self.lab_view._resource_requester.priority

    @priority.setter
    def priority(self, value: Union[int, TaskPriority]):
        if value < 0:
            raise ValueError("Priority should be a positive integer")
        self.lab_view._resource_requester.priority = int(value)

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
        raise NotImplementedError()

    def run_subtask(self, *args, **kwargs):
        """
        Run a subtask of this current task. Returns the result, if any, of the subtask.
        """
        return self.lab_view.run_subtask(*args, **kwargs)


_task_registry: Dict[str, Type[BaseTask]] = {}

SUPPORTED_SAMPLE_POSITIONS_TYPE = Dict[
    Union[Type[BaseDevice], str, None], Union[str, List[str]]
]
_reroute_task_registry: List[
    Dict[str, Union[Type[BaseTask], SUPPORTED_SAMPLE_POSITIONS_TYPE]]
] = []


def add_task(task: Type[BaseTask]):
    """
    Register a task
    """
    if task.__name__ in _task_registry:
        raise KeyError(f"Duplicated operation name {task.__name__}")
    _task_registry[task.__name__] = task


def get_all_tasks() -> Dict[str, Type[BaseTask]]:
    """
    Get all the tasks in the registry
    """
    return _task_registry.copy()


def add_reroute_task(
    supported_sample_positions: SUPPORTED_SAMPLE_POSITIONS_TYPE,
    task: Type[BaseTask],
    **kwargs,
):
    """
    Register a reroute task
    """
    if task.__name__ not in _task_registry:
        raise KeyError(
            f"Task {task.__name__} is not registered! Register with `add_task` before registering as a reroute task."
        )
    if "sample" not in getfullargspec(task).args:
        raise ValueError(
            f"Task {task.__name__} does not have `sample` as a parameter! "
            "Reroute tasks must accept a `sample` parameter that specifies the name or sample_id of the sample to be rerouted"
        )
    _reroute_task_registry.append(
        {
            "supported_sample_positions": supported_sample_positions,
            "task": task,
            "kwargs": kwargs,
        }
    )
