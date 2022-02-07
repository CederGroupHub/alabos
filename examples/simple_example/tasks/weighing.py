import time

from alab_management.task_view.task import BaseTask
from bson import ObjectId

from .moving import Moving
from ..devices.scale import Scale


class Weighing(BaseTask):
    def __init__(self, sample: ObjectId, *args, **kwargs):
        super(Weighing, self).__init__(*args, **kwargs)
        self.sample = sample

    def run(self):
        with self.lab_view.request_resources({Scale: ["$/inside"],
                                              None: ["furnace_table"]}) as devices_and_positions:
            devices, sample_positions = devices_and_positions
            scale: Scale = devices[Scale]

            moving_into_scale = Moving(sample=self.sample,
                                       task_id=self.task_id,
                                       dest=sample_positions[Scale]["$/inside"][0],
                                       lab_view=self.lab_view,
                                       logger=self.logger)
            moving_into_scale.run()

            time.sleep(5)
            image = scale.read_data()
            self.logger.log_amount({
                "type": "image/jpeg",
                "data": image,
                "sample_id": self.sample,
            })

            moving_out_scale = Moving(
                self.sample,
                task_id=self.task_id,
                dest=sample_positions[None]["furnace_table"][0],
                lab_view=self.lab_view,
                logger=self.logger)
            moving_out_scale.run()
