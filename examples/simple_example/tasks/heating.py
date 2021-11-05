from typing import List, Tuple, Optional

from bson import ObjectId

from alab_management import BaseTask
from ..devices.furnace import Furnace
from .moving import Moving


class Heating(BaseTask):
    LONG_TIME_TASK = True

    def __init__(self, sample_1: ObjectId, sample_2: Optional[ObjectId],
                 sample_3: Optional[ObjectId], sample_4: Optional[ObjectId],
                 setpoints: List[Tuple[float, float]], *args, **kwargs):
        super(Heating, self).__init__(*args, **kwargs)
        self.setpoints = setpoints
        self.samples = [sample_1, sample_2, sample_3, sample_4]

    def run(self):
        with self.lab_manager.request_resources({Furnace: [("$.inside", 4)]}) as devices_and_positions:
            devices, sample_positions = devices_and_positions
            furnace = devices[Furnace]
            inside_furnace = sample_positions[Furnace]["$.inside"]

            for sample in self.samples:
                moving_task = Moving(sample=sample,
                                     task_id=self.task_id,
                                     dest=inside_furnace[0],
                                     lab_manager=self.lab_manager,
                                     logger=self.logger)
                moving_task.run()

            furnace.run_program(self.setpoints)

            while furnace.is_running():
                self.logger.log_device_signal({
                    "device": furnace.name,
                    "temperature": furnace.get_temperature(),
                })
