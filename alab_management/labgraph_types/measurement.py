from abc import abstractmethod
from ..task_view import BaseTask, TaskPriority
from typing import Optional, List, Union, TYPE_CHECKING
from bson import ObjectId
from labgraph import Measurement, Actor

if TYPE_CHECKING:
    from alab_management.lab_view import LabView

placeholder_actor = Actor(
    name="Placeholder before execution", description="Placeholder before execution"
)
placeholder_actor.save()


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
            actor=placeholder_actor,
            # parameters=self.subclass_kwargs,
            # *args,
            parameters=kwargs,
        )

    def to_dict(self):
        d = BaseTask.to_dict(self)
        d.update(Measurement.to_dict(self))
        return d

    def __eq__(self, other):
        try:
            return self.to_dict() == other.to_dict()
        except:
            return False
