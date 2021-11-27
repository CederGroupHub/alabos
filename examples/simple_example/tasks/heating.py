import time

from alab_management import BaseTask
from bson import ObjectId

from .moving import Moving
from ..devices.furnace import Furnace


class Heating(BaseTask):

    def __init__(self, sample: ObjectId, heating_time: float, heating_temperature: float, *args, **kwargs):
        super(Heating, self).__init__(*args, **kwargs)
        self.heating_time = heating_time
        self.heating_temperature = heating_temperature
        self.sample = sample

    def run(self):
        with self.lab_manager.request_resources({Furnace: ["$/inside"]}) as (devices, sample_positions):
            furnace = devices[Furnace]
            move_to_furnace = Moving(sample=self.sample,
                                     task_id=self.task_id,
                                     dest=sample_positions[Furnace]["$/inside"][0],
                                     lab_manager=self.lab_manager)
            move_to_furnace.run()

            furnace.run_program(heating_time=self.heating_time, heating_temperature=self.heating_temperature)

            while furnace.is_running():
                self.logger.log_device_signal({
                    "device": furnace.name,
                    "temperature": furnace.get_temperature(),
                })
                time.sleep(30)

        with self.lab_manager.request_resources({None: ["furnace_table"]}) as (devices, sample_positions):
            move_out_furnace = Moving(sample=self.sample,
                                      task_id=self.task_id,
                                      dest=sample_positions[None]["furnace_table"][0],
                                      lab_manager=self.lab_manager,
                                      logger=self.logger)
            move_out_furnace.run()
