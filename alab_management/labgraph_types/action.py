from abc import abstractmethod
from ..task_view import BaseTask, TaskPriority, TaskView
from typing import Optional, List, Union, TYPE_CHECKING
from bson import ObjectId
from labgraph import Ingredient, WholeIngredient, Material, Action, Actor
from .placeholders import placeholder_actor

if TYPE_CHECKING:
    from alab_management.lab_view import LabView


class BaseAction(BaseTask, Action):
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
            labgraph_type="Action",
        )

        Action.__init__(
            self,
            name=self.__class__.__name__,
            actor=placeholder_actor,
            parameters=kwargs,
            # description="An Action Task defined in ALabOS",  # TODO add description
            # *args,
            # **kwargs,
        )

    # def get_ingredients(self) -> List[Ingredient]:
    #     upstream_tasks = self.lab_view.get_previous_tasks()
    #     if len(upstream_tasks) == 0:
    #         return (
    #             []
    #         )  # first task will generate a material, will default to having no upstream materials
    #     else:
    #         ingredients = []
    #         for task in upstream_tasks:
    #             materials = [
    #                 Material.get(material_id)
    #                 for material_id in task["materials_generated"]
    #             ]
    #             ingredients.extend(
    #                 [WholeIngredient(material=material) for material in materials]
    #             )

    #         return ingredients

    # def create_materials(self) -> List[Material]:
    #     return []  # TODO

    # def to_dict(self):
    #     d = BaseTask.to_dict(self)
    #     d.update(Action.to_dict(self))
    #     return d

    def __eq__(self, other):
        try:
            return self.to_dict() == other.to_dict()
        except:
            return False
