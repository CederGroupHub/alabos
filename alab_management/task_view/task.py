"""
Define the base class of task, which will be used for defining more tasks.
"""
from abc import ABC, abstractmethod
import inspect
from typing import Dict, List, Type, TYPE_CHECKING, Optional, Union, Any
from bson.objectid import ObjectId
from alab_management.task_view.task_enums import TaskPriority
from inspect import getfullargspec
from alab_management.builders.samplebuilder import SampleBuilder
from alab_management.builders.experimentbuilder import ExperimentBuilder
from alab_management.utils.data_objects import make_bsonable

if TYPE_CHECKING:
    from alab_management.lab_view import LabView
    from alab_management.device_view.device import BaseDevice


class BaseTask(ABC):
    """
    The abstract class of task.

    All the tasks should inherit from this class.
    """

    def __init__(
        self,
        samples: Optional[List[str]] = None,
        task_id: Optional[ObjectId] = None,
        lab_view: Optional["LabView"] = None,
        priority: Optional[Union[TaskPriority, int]] = TaskPriority.NORMAL,
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

        self.child_task_num: int = 0
        self.__samples = samples or []
        if self.is_simulation:
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
                    "BaseTask was instantiated with simulation mode off -- task_id, lab_view, and samples must all be provided!"
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
        return self.__simulation

    @property
    def samples(self) -> List[str]:
        return self.__samples

    @property
    def priority(self) -> int:
        if self.is_simulation:
            return 0
        return self.lab_view._resource_requester.priority

    @priority.setter
    def priority(self, value: Union[int, TaskPriority]):
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
        return self._message

    # @abstractmethod
    def validate(self) -> bool:
        """
        Validate the task. This function will be called before the task is executed. Should return False if the task has values that make it impossible to execute.

        For example, a `Heating` subclass of `BaseTask` might return False if the set temperature is too high for the furnace.
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
        task: Type["BaseTask"],
        samples: Optional[Union[List[str], str]] = None,
        **kwargs,
    ):
        """
        Run a subtask of this current task. Returns the result, if any, of the subtask.
        """
        samples = samples or self.samples
        if isinstance(samples, str):
            samples = [samples]
        return self.lab_view.run_subtask(task=task, samples=samples, **kwargs)

    def add_to(
        self,
        samples: Union[SampleBuilder, List[SampleBuilder]],
    ):
        """Used to add basetask to a SampleBuilder's tasklist during Experiment construction.

        Args:
            samples (Union[SampleBuilder, List[SampleBuilder]]): One or more SampleBuilder's which will have this task appended to their tasklists.
        """
        if not self.__simulation:
            raise RuntimeError(
                "Cannot add a live BaseTask instance to a SampleBuilder. BaseTask must be instantiated with `simulation=True` to enable this method."
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


_task_registry: Dict[str, Type[BaseTask]] = {}

SUPPORTED_SAMPLE_POSITIONS_TYPE = Dict[
    Union[Type["BaseDevice"], str, None], Union[str, List[str]]
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
