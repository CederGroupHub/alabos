from typing import List, Tuple

from bson import ObjectId

from alab_management import BaseTask
from .moving import Moving
from ..devices.furnace import Furnace


class Heating(BaseTask):

    def __init__(self, sample: ObjectId, heating_time: float, heating_temperature: float, *args, **kwargs):
        super(Heating, self).__init__(*args, **kwargs)
        self.heating_time = heating_time
        self.heating_temperature = heating_temperature
        self.sample = sample

    def run(self):
        with self.lab_manager.request_resources({Furnace: ["$.inside"]}) as devices_and_positions:
            devices, sample_positions = devices_and_positions
            furnace = devices[Furnace]

            moving_task = Moving(sample=self.sample,
                                 task_id=self.task_id,
                                 dest=sample_positions[Furnace]["$.inside"],
                                 lab_manager=self.lab_manager,
                                 logger=self.logger)
            moving_task.run()

            furnace.run_program(heating_time=self.heating_time, heating_temperature=self.heating_temperature)

            while furnace.is_running():
                self.logger.log_device_signal({
                    "device": furnace.name,
                    "temperature": furnace.get_temperature(),
                })
