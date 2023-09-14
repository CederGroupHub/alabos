import time
from datetime import timedelta
from typing import ClassVar

from alab_control.furnace_epc_3016 import FurnaceController, Segment, SegmentType

from alab_management import BaseDevice, SamplePosition


class Furnace(BaseDevice):
    description: ClassVar[str] = "Simple furnace"

    def __init__(self, address: str, port: int = 502, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.address = address
        self.port = port
        self.driver = FurnaceController(address=address, port=port)

    @property
    def sample_positions(self):
        return [
            SamplePosition(
                f"{self.name}/inside",
                description="The position inside the furnace, where the samples are heated",
            ),
            SamplePosition(
                "furnace_table", description="Temporary position to transfer samples"
            ),
        ]

    def emergent_stop(self):
        self.driver.stop()

    def run_program(self, heating_time: float, heating_temperature: float):
        segments = [
            Segment(
                segment_type=SegmentType.RAMP_RATE,
                target_setpoint=heating_temperature,
                ramp_rate_per_sec=10,
            ),
            Segment(
                segment_type=SegmentType.DWELL,
                duration=timedelta(hours=heating_time),
            ),
            Segment(
                segment_type=SegmentType.STEP,
                target_setpoint=0,
            ),
            Segment(
                segment_type=SegmentType.END,
            ),
        ]
        self.driver.run_program(*segments)
        time.sleep(2)

    def is_running(self):
        return self.driver.is_running()

    def get_temperature(self):
        return self.driver.current_temperature
