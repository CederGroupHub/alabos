from abc import abstractmethod
from ..task_view import BaseTask, TaskPriority
from typing import Optional, List, Union, TYPE_CHECKING
from bson import ObjectId

if TYPE_CHECKING:
    from alab_management.lab_view import LabView


class BaseAnalysis(BaseTask):
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
        super().__init__(
            samples=samples,
            task_id=task_id,
            lab_view=lab_view,
            priority=priority,
            simulation=simulation,
            *args,
            **kwargs,
        )

    def get_previous_measurements(
        self, name: Optional[str] = None
    ) -> List[Optional[dict]]:
        """Get measurement(s) immediately upstream of this analysis. If name is specified, only return measurements with that name.

        Args:
            name (Optional[str], optional): Name of the measurement task. Defaults to None, in which case all measurements immediately upstream of this analysis are returned.

        Returns:
            List[Optional[dict]]: Dictionary entries of the measurement tasks. Note the task results will be nested under the "result" key.
        """

        upstream_tasks = self.lab_view.get_previous_tasks()

        return [
            task
            for task in upstream_tasks
            if task["type"] == "Measurement" and (name is None or task["name"] == name)
        ]

    def get_previous_analyses(self, name: Optional[str] = None) -> List[Optional[dict]]:
        """Get analysis(es) immediately upstream of this analysis. If name is specified, only return analyses with that name.

        Args:
            name (Optional[str], optional): Name of the analysis task. Defaults to None, in which case all analyses immediately upstream of this analysis are returned.

        Returns:
            List[Optional[dict]]: Dictionary entries of the analysis tasks. Note the task results will be nested under the "result" key.
        """

        upstream_tasks = self.lab_view.get_previous_tasks()

        return [
            task
            for task in upstream_tasks
            if task["type"] == "Analysis" and (name is None or task["name"] == name)
        ]
