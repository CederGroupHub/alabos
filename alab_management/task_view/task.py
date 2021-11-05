"""
Define the base class of task
"""
from abc import ABC, abstractmethod
from typing import Dict, Type

from bson import ObjectId


class BaseTask(ABC):
    """
    The abstract class of task.

    All the tasks should inherit from this class.

    - ``task_id``: the identifier of task
    - ``lab_manager``: you can request devices and positions from it
    """
    LONG_TIME_TASK = None

    def __init__(self, task_id: ObjectId, lab_manager, logger):
        self.task_id = task_id
        self.lab_manager = lab_manager
        self.logger = logger

    @abstractmethod
    def run(self):
        """
        Run the task
        """
        raise NotImplementedError()


_task_registry: Dict[str, Type[BaseTask]] = {}


def add_task(task: Type[BaseTask]):
    """
    Register a task
    """
    if task.__name__ in _task_registry:
        raise KeyError("Duplicated operation name {}".format(task.__name__))
    _task_registry[task.__name__] = task


def get_all_tasks() -> Dict[str, Type[BaseTask]]:
    """
    Get all the tasks in the registry
    """
    return _task_registry.copy()
