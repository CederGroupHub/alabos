from dataclasses import dataclass

from bson import ObjectId

from alab_management.task_view.task import BaseTask


@dataclass
class Starting(BaseTask):
    def __init__(self, sample: ObjectId, dest: str, *args, **kwargs):
        super(Starting, self).__init__(*args, **kwargs)
        self.sample = sample
        self.dest = dest

    def run(self):
        with self.lab_manager.request_sample_positions([self.dest]) as sample_positions:
            self.lab_manager.move_sample(self.sample, sample_positions[self.dest])