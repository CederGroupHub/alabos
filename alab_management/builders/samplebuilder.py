"""Build the sample object."""

from typing import TYPE_CHECKING, Any, Dict, List, Optional

from bson import ObjectId

if TYPE_CHECKING:
    from alab_management.builders.experimentbuilder import ExperimentBuilder


class SampleBuilder:
    """
    Build a sample.

    Each sample has a name, tags, and metadata. Each sample also
    has a list of tasks which are binded to it. Each sample is a node in a directed graph of tasks.
    Each task has a list of samples which are binded to it. Each sample also has a list of tags and
    metadata. The tags and metadata are used to filter the samples and tasks. The tags and metadata are
    also used to group the samples and tasks.
    """

    def __init__(
        self,
        name: str,
        experiment: "ExperimentBuilder",
        tags: Optional[List[str]] = None,
        **metadata,
    ):
        self.name = name
        self._tasks: List[str] = []  # type: ignore
        self.experiment = experiment
        self.metadata = metadata
        self._id = str(ObjectId())
        self.tags = tags or []

    def add_task(
        self,
        task_id: str,
    ) -> None:
        """
        Add a task to the sample. You should use this function only for special cases which
        are not handled by the `add_sample` function.

        Args:
            task_id (str): The object id of the task in mongodb
        Returns:
            None.
        """
        if task_id not in self._tasks:
            self._tasks.append(task_id)

    def to_dict(self) -> Dict[str, Any]:
        """Return Sample as a dictionary.

        This looks like:
        {
            "_id": str(ObjectId),
            "name": str,
            "tags": List[str],
            "metadata": Dict[str, Any],
        }

        Returns
        -------
            Dict[str, Any]: sample as a dictionary
        """
        return {
            "_id": str(self._id),
            "name": self.name,
            "tags": self.tags,
            "metadata": self.metadata,
        }

    @property
    def tasks(self):
        """Return the tasks binded to this sample."""
        return self._tasks

    def __eq__(self, other):
        """Check if two samples are equal."""
        return self._id == other._id

    def __repr__(self):
        """Return a string representation of the sample."""
        return f"<Sample: {self.name}>"


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
