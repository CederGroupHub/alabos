from abc import abstractmethod
from ..task_view import BaseTask, TaskPriority, TaskStatus
from typing import Optional, List, Union, TYPE_CHECKING
from bson import ObjectId
from labgraph import Measurement, Actor
from .placeholders import PLACEHOLDER_ACTOR_FOR_TASKS_THAT_HAVENT_RUN_YET

if TYPE_CHECKING:
    from alab_management.lab_view import LabView


class BaseMeasurement(BaseTask, Measurement):
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
        BaseTask.__init__(
            self,
            samples=samples,
            task_id=task_id,
            lab_view=lab_view,
            priority=priority,
            simulation=simulation,
            labgraph_type="Measurement",
            # *args,
            # **kwargs,
        )

        Measurement.__init__(
            self,
            name=self.__class__.__name__,
            actor=PLACEHOLDER_ACTOR_FOR_TASKS_THAT_HAVENT_RUN_YET,
            # parameters=self.subclass_kwargs,
            # *args,
            parameters=kwargs,
            status=TaskStatus.PLANNED.name,
        )

        self._id = self.task_id  # sync with BaseTask

    def __eq__(self, other):
        try:
            return self.to_dict() == other.to_dict()
        except:
            return False
