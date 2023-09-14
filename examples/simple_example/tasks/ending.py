from bson import ObjectId

from alab_management import BaseTask


class Ending(BaseTask):
    def __init__(self, sample: ObjectId, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.sample = sample

    def run(self):
        self.lab_view.move_sample(sample_id=self.sample, position=None)
