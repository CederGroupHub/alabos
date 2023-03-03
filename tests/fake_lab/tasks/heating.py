import time
from typing import List, Tuple

from bson import ObjectId

from alab_management import BaseTask
from .moving import Moving
from ..devices.furnace import Furnace


class Heating(BaseTask):
    def __init__(
        self,
        samples: List[ObjectId],
        setpoints: List[Tuple[float, float]],
        *args,
        **kwargs
    ):
        super(Heating, self).__init__(samples=samples, *args, **kwargs)
        self.setpoints = setpoints
        self.sample = samples[0]

    def run(self):
        with self.lab_view.request_resources({Furnace: {"inside": 1}}) as (
            devices,
            sample_positions,
        ):
            furnace = devices[Furnace]
            inside_furnace = sample_positions[Furnace]["inside"][0]

            moving_task = Moving(
                sample=self.sample,
                task_id=self.task_id,
                dest=inside_furnace,
                lab_view=self.lab_view,
            )
            moving_task.run()

            furnace.run_program(self.setpoints)

            while furnace.is_running():
                self.logger.log_device_signal(
                    {
                        "device": furnace.name,
                        "temperature": furnace.get_temperature(),
                    }
                )
                time.sleep(1)
        return self.task_id
