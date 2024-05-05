import time

from bson import ObjectId

from alab_management.task_view import BaseTask

from ..devices.furnace import Furnace  # noqa
from .moving import Moving


class Heating(BaseTask):
    def __init__(
        self,
        samples: list[ObjectId],
        setpoints: list[tuple[float, float]],
        *args,
        **kwargs,
    ):
        super().__init__(samples=samples, *args, **kwargs)
        self.setpoints = setpoints

    def run(self):
        with self.lab_view.request_resources({Furnace: {"inside": 8}}) as (
            devices,
            sample_positions,
        ):
            furnace = devices[Furnace]
            inside_furnaces = sample_positions[Furnace]["inside"]

            for sample, inside_furnace in zip(self.samples, inside_furnaces):
                self.lab_view.run_subtask(
                    Moving,
                    sample=sample,
                    samples=self.samples,
                    dest=inside_furnace,
                )

            furnace.run_program(self.setpoints)

            while furnace.is_running():
                self.logger.log_device_signal(
                    device_name=furnace.name,
                    signal_name="Temperature",
                    signal_value=furnace.get_temperature(),
                )
                time.sleep(1)
        return self.task_id
