from bson import ObjectId

from alab_management.task_view.task import BaseTask


class DefaultTask(BaseTask):
    def __init__(self, sample: ObjectId, *args, **kwargs):
        super(DefaultTask, self).__init__(*args, **kwargs)
        self.sample = sample

    def run(self):
        with self.lab_manager.request_resources({None: [{"prefix": "DefaultSamplePosition", "number": 2}]}) \
                as (devices, sample_positions):
            self.lab_manager.move_sample(self.sample, sample_positions[None]["DefaultSamplePosition"][0])
