from typing import Any, List, Dict, TYPE_CHECKING, Optional, Set, Union

from bson import ObjectId

if TYPE_CHECKING:
    from alab_management.builders.experimentbuilder import ExperimentBuilder



from alab_management.labgraph_types.action import BaseAction
from alab_management.labgraph_types.analysis import BaseAnalysis
from alab_management.labgraph_types.measurement import BaseMeasurement
from labgraph import Sample as LabgraphSample, Material, Measurement, Analysis
from labgraph.data.nodes import UnspecifiedAmountIngredient

from typing import List


class SampleBuilder(LabgraphSample):
    def __init__(
        self,
        name: str,
        description: str,
        tags: Optional[List[str]] = None,
        *args,
        **kwargs,
    ):
        self.current_material = None

        super().__init__(
            name=name, description=description, tags=tags or [], *args, **kwargs
        )

    def add_action(
        self,
        task: BaseAction,
        input_materials: Optional[List[Material]] = None,
        generated_materials: Optional[List[Material]] = None,
    ):
        if input_materials:
            for material in input_materials:
                task.add_ingredient(UnspecifiedAmountIngredient(material))
        elif self.current_material:
            task.add_ingredient(
                UnspecifiedAmountIngredient(material=self.current_material)
            )

        if generated_materials:
            for material in generated_materials:
                task.add_generated_material(material)
                self.add_node(material)
            self.current_material = generated_materials[0]
        else:
            generated_material = task.make_generic_generated_material()
            self.add_node(generated_material)
            self.current_material = generated_material

        self.add_node(task)
        return task

    def add_measurement(
        self, task: BaseMeasurement, input_material: Optional[Material] = None
    ):
        material = None

        if input_material:
            if input_material not in self.nodes:
                raise ValueError(
                    f"The input material must be a node in the labgraph sample! We do not yet contain ({input_material})"
                )
            material = input_material
        elif self.current_material:
            material = self.current_material
        else:
            raise ValueError(
                "No material has been generated in this sample yet. To add a measurement, you either specify the input material or first add an action that generates a material!"
            )

        task.material = material
        self.add_node(task)
        return task

    def add_analysis(
        self,
        task: BaseAnalysis,
        input_measurements: Optional[List[Measurement]] = None,
        input_analyses: Optional[List[Analysis]] = None,
    ):
        if not input_measurements and not input_analyses:
            raise ValueError(
                "You must specify either input measurements or input analyses!"
            )

        for measurement in input_measurements or []:
            task.add_measurement(measurement)
        for analysis in input_analyses or []:
            task.add_upstream_analysis(analysis)

        self.add_node(task)

        return task


# class SampleBuilder:
#     def __init__(
#         self,
#         name: str,
#         experiment: "ExperimentBuilder",
#         tags: Optional[List[str]] = None,
#         **metadata,
#     ):
#         self.name = name
#         self._tasks: List[str] = []  # type: ignore
#         self.experiment = experiment
#         self.metadata = metadata
#         self._id = str(ObjectId())
#         self.tags = tags or []

#     def add_task(
#         self,
#         task_id: str,
#     ) -> None:
#         if task_id not in self._tasks:
#             self._tasks.append(task_id)

#     def to_dict(self) -> Dict[str, Any]:
#         """Return Sample as a dictionary. This looks like:

#         {
#             "_id": str(ObjectId),
#             "name": str,
#             "tags": List[str],
#             "metadata": Dict[str, Any],
#         }

#         Returns:
#             Dict[str, Any]: sample as a dictionary
#         """
#         return {
#             "_id": str(self._id),
#             "name": self.name,
#             "tags": self.tags,
#             "metadata": self.metadata,
#         }

#     @property
#     def tasks(self):
#         return self._tasks

#     def __eq__(self, other):
#         return self._id == other._id

#     def __repr__(self):
#         return f"<Sample: {self.name}>"


# ## Format checking for API inputs


# class TaskInputFormat(BaseModel):
#     id: Optional[Any] = Field(None, alias="id")
#     type: str
#     parameters: Dict[str, Any]
#     capacity: int
#     prev_tasks: List[str]
#     samples: List[Union[str, Any]]

#     @validator("id")
#     def must_be_valid_objectid(cls, v):
#         try:
#             ObjectId(v)
#         except:
#             raise ValueError(f"Received invalid _id: {v} is not a valid ObjectId!")
#         return v

#     @validator("capacity")
#     def must_be_positive(cls, v):
#         if v < 0:
#             raise ValueError(f"Capacity must be positive, received {v}")
#         return v

#     @validator("samples")
#     def samples_must_be_valid_objectid(cls, v):
#         for sample_id in v:
#             try:
#                 ObjectId(sample_id)
#             except:
#                 raise ValueError(
#                     f"Received invalid sample_id: {sample_id} is not a valid ObjectId!"
#                 )
#         return v

#     @validator("prev_tasks")
#     def prevtasks_must_be_valid_objectid(cls, v):
#         for task_id in v:
#             try:
#                 ObjectId(task_id)
#             except:
#                 raise ValueError(
#                     f"Received invalid sample_id: {task_id} is not a valid ObjectId!"
#                 )
#         return v


# class SampleInputFormat(BaseModel):
#     """
#     Format check for API for Sample submission. Sample's must follow this format to be accepted into the batching queue.
#     """

#     id: Optional[Any] = Field(None, alias="id")
#     name: constr(regex=r"^[^$.]+$")  # type: ignore
#     tags: List[str]
#     tasks: List[TaskInputFormat]
#     metadata: Dict[str, Any]

#     @validator("id")
#     def must_be_valid_objectid(cls, v):
#         try:
#             ObjectId(v)
#         except:
#             raise ValueError(f"Received invalid _id: {v} is not a valid ObjectId!")
#         return v
