"""Build the sample object."""

from typing import TYPE_CHECKING, Any

from bson import ObjectId  # type: ignore

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
        tags: list[str] | None = None,
        **metadata,
    ):
        self.name = name
        self._tasks: list[str] = []  # type: ignore
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

    def to_dict(self) -> dict[str, Any]:
        """Return Sample as a dictionary.

        This looks like:

        .. code-block::

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
