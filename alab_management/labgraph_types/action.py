from abc import abstractmethod
from ..task_view import BaseTask, TaskPriority, TaskView
from typing import Optional, List, Union, TYPE_CHECKING
from bson import ObjectId
from labgraph import Ingredient, WholeIngredient, Material

if TYPE_CHECKING:
    from alab_management.lab_view import LabView


class BaseAction(BaseTask):
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

    def get_ingredients(self) -> List[Ingredient]:
        upstream_tasks = self.lab_view.get_previous_tasks()
        if len(upstream_tasks) == 0:
            return (
                []
            )  # first task will generate a material, will default to having no upstream materials
        else:
            ingredients = []
            for task in upstream_tasks:
                materials = [
                    Material.get(material_id)
                    for material_id in task["materials_generated"]
                ]
                ingredients.extend(
                    [WholeIngredient(material=material) for material in materials]
                )

            return ingredients

    def create_materials(self) -> List[Material]:
        return []  # TODO
