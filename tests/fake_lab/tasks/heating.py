import time
from typing import List, Tuple

from bson import ObjectId

from alab_management import BaseTask
from .moving import Moving
from ..devices.furnace import Furnace
from alab_management.lab_manager import ResourcesRequest


class Heating(BaseTask):
    def __init__(self, sample: ObjectId,
                 setpoints: List[Tuple[float, float]], *args, **kwargs):
        super(Heating, self).__init__(*args, **kwargs)
        self.setpoints = setpoints
        self.sample = sample

    def run(self):
        with self.lab_manager.request_resources({Furnace: ["$.inside"]}) as devices_and_positions:
            devices, sample_positions = devices_and_positions
            furnace = devices[Furnace]
            inside_furnace = sample_positions[Furnace]["$.inside"]

            moving_task = Moving(sample=self.sample,
                                 task_id=self.task_id,
                                 dest=inside_furnace,
                                 lab_manager=self.lab_manager,
                                 logger=self.logger)
            moving_task.run()

            furnace.run_program(self.setpoints)

            while furnace.is_running():
                self.logger.log_device_signal({
                    "device": furnace.name,
                    "temperature": furnace.get_temperature(),
                })
                time.sleep(1)
