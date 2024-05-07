from bson import ObjectId

from alab_management.task_view.task import BaseTask


class InfiniteTask(BaseTask):
    def __init__(self, samples: list[ObjectId], *args, **kwargs):
        super().__init__(samples=samples, *args, **kwargs)
        self.sample = samples[0]

    def run(self):
        while True:
            pass
