from bson import ObjectId

from alab_management.task_view.task import BaseTask


class Starting(BaseTask):
    def __init__(self, sample: ObjectId, dest: str, *args, **kwargs):
        super(Starting, self).__init__(*args, **kwargs)
        self.sample = sample
        self.dest = dest

    def run(self):
        with self.lab_manager.request_resources({None: [self.dest]}) as (devices, sample_positions):
            self.lab_manager.move_sample(self.sample, sample_positions[None][self.dest][0])
        return self.task_id