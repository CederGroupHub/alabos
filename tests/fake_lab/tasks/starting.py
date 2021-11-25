from dataclasses import dataclass

from bson import ObjectId

from alab_management.task_view.task import BaseTask


@dataclass
class Starting(BaseTask):
    def __init__(self, sample: ObjectId, dest: str, *args, **kwargs):
        super(Starting, self).__init__(*args, **kwargs)
        self.sample = sample
        self.dest = dest

    def required_resources(self):
        return {None: [self.dest]}

    def run(self, devices, sample_positions):
        self.lab_manager.move_sample(self.sample, sample_positions[None][self.dest][0])
