from bson import ObjectId  # type: ignore
from pydantic import BaseModel

from alab_management.task_view.task import BaseTask


class DefaultTask(BaseTask):
    """The default task, refer to https://idocx.github.io/alab_management/task_definition.html for more details. #TODO"""

    def __init__(self, sample: ObjectId, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.sample = sample

    def run(self):
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
        pass
