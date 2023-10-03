from bson import ObjectId
from typing import List
from alab_management.task_view.task import BaseTask


class Ending(BaseTask):
    def __init__(self, samples: List[ObjectId], *args, **kwargs):
        super(Ending, self).__init__(samples=samples, *args, **kwargs)
        self.sample = samples[0]

    def run(self):
        self.lab_view.move_sample(self.sample, None)
        return self.task_id
