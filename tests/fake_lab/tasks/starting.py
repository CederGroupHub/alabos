import time
from typing import List

from bson import ObjectId

from alab_management.task_view.task import BaseTask


class Starting(BaseTask):
    def __init__(self, samples: List[ObjectId], dest: str, *args, **kwargs):
        super(Starting, self).__init__(samples=samples, *args, **kwargs)
        self.sample = samples[0]
        self.dest = dest

    def run(self):
        with self.lab_view.request_resources({None: {self.dest: 1}}) as (
            devices,
            sample_positions,
        ):
            self.lab_view.move_sample(self.sample, sample_positions[None][self.dest][0])
            time.sleep(15)
        return self.task_id
