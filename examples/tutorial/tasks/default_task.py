from bson import ObjectId  # type: ignore
from pydantic import BaseModel

from alab_management.task_view.task import BaseTask


class DefaultTask(BaseTask):
    """The default task, refer to https://idocx.github.io/alab_management/task_definition.html for more details. #TODO"""

    def __init__(self, sample: ObjectId, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.sample = sample

    def run(self):
        """
        The main logic of the task.

        You can request resources, move samples, and communicate with devices in this method.
        Finally, the return value of this method will be stored as the result of the task (valiated
        by `result_specification`).
        """
        with self.lab_view.request_resources({None: {"DefaultSamplePosition": 1}}) as (
            _,
            sample_positions,
        ):
            self.lab_view.move_sample(
                self.sample, sample_positions[None]["DefaultSamplePosition"][0]
            )

    def validate(self) -> bool:
        """
        Validation of the input parameters.

        You can add more validation logic here. The method should return True if the input parameters
        are valid, False otherwise. This method is called when you build the task.
        """
        return True

    @property
    def result_specification(self) -> type[BaseModel]:
        """
        The result specification of the task.

        The method should return a pydantic model that defines the result of the task. The result
        will be validated using the result_specification.
        """

        class DefaultTaskResult(BaseModel):
            """The result of the default task."""

            mass: float
            temperature: float

        return DefaultTaskResult
