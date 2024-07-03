from typing import ClassVar

from alab_management import value_in_database
from alab_management.device_view import BaseDevice
from alab_management.sample_view import SamplePosition


class RobotArm(BaseDevice):
    description: ClassVar[str] = "Fake robot arm"
    ensure_single_creation = value_in_database("ensure_single_creation", 0)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    @property
    def sample_positions(self):
        return [
            SamplePosition(
                "sample_holder",
                description="The position that can hold the sample",
            ),
        ]

    def emergent_stop(self):
        pass

    def run_program(self, program):
        pass

    def is_running(self) -> bool:
        return False

    def connect(self):
        if self.ensure_single_creation != 0:
            raise ValueError("Robot arm already connected")
        self.ensure_single_creation = 1

    def disconnect(self):
        if self.ensure_single_creation != 1:
            raise ValueError("Robot arm not connected")
        self.ensure_single_creation = 0
