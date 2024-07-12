from importlib import util
from pathlib import Path
from typing import ClassVar

from alab_management.device_view import BaseDevice
from alab_management.sample_view import SamplePosition


class RobotArm(BaseDevice):
    description: ClassVar[str] = "Fake robot arm"

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

    def get_most_recent_picture_location(self):
        return (
            Path(
                util.find_spec("alab_management").origin.split("__init__.py")[0]
            ).parent
            / "tests"
            / "fake_lab"
            / "large_file_example.zip"
        )

    def is_running(self) -> bool:
        return False

    def connect(self):
        pass

    def disconnect(self):
        pass
