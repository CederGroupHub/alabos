from bson import ObjectId

from alab_management.task_view.task import BaseTask


class DefaultTask(BaseTask):
    """
    The default task, refer to https://idocx.github.io/alab_management/task_definition.html for more details
    """

    def __init__(self, sample: ObjectId, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.sample = sample

    def run(self):
        with self.lab_view.request_resources({None: [{"prefix": "DefaultSamplePosition", "number": 2}]}) \
                as (_, sample_positions):
            self.lab_view.move_sample(self.sample, sample_positions[None]["DefaultSamplePosition"][0])
