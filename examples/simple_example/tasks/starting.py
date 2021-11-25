from alab_management import BaseTask
from bson import ObjectId


class Starting(BaseTask):

    def __init__(self, sample: ObjectId, start_position: str, *args, **kwargs):
        super(Starting, self).__init__(*args, **kwargs)
        self.start_position = start_position
        self.sample = sample

    def required_resources(self):
        return {}

    def run(self, devices, sample_positions):
        with self.lab_manager.request_resources({None: [self.start_position]}) as (devices, sample_positions):
            self.lab_manager.move_sample(sample_id=self.sample,
                                         position=sample_positions[None][self.start_position][0])
