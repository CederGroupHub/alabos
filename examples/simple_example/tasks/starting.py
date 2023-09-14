from bson import ObjectId

from alab_management import BaseTask


class Starting(BaseTask):
    def __init__(self, sample: ObjectId, start_position: str, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.start_position = start_position
        self.sample = sample

    def run(self):
        with self.lab_view.request_resources({None: [self.start_position]}) as (
            devices,
            sample_positions,
        ):
            self.lab_view.move_sample(
                sample_id=self.sample,
                position=sample_positions[None][self.start_position][0],
            )
