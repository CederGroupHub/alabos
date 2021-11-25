from alab_management import BaseTask
from bson import ObjectId


class Ending(BaseTask):

    def __init__(self, sample: ObjectId, *args, **kwargs):
        super(Ending, self).__init__(*args, **kwargs)
        self.sample = sample

    def required_resources(self):
        return {}

    def run(self, devices, sample_positions):
        self.lab_manager.move_sample(sample_id=self.sample, position=None)
