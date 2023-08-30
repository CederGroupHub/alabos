from abc import abstractmethod
from ..task_view import BaseTask, TaskPriority
from typing import Optional, List, Union, TYPE_CHECKING
from bson import ObjectId
from labgraph import Analysis
from .placeholders import placeholder_actor

if TYPE_CHECKING:
    from alab_management.lab_view import LabView


class BaseAnalysis(BaseTask, Analysis):
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
            labgraph_type="Analysis",
            # *args,
            # **kwargs,
        )

        Analysis.__init__(
            self,
            name=self.__class__.__name__,
            actor=placeholder_actor,
            parameters=kwargs,
        )

    def to_dict(self):
        d = BaseTask.to_dict(self)
        d.update(Analysis.to_dict(self))
        return d

    def __eq__(self, other):
        try:
            return self.to_dict() == other.to_dict()
        except:
            return False
