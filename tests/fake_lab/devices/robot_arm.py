from threading import Timer
from pathlib import Path
from typing import ClassVar

from alab_management.device_view import BaseDevice
from alab_management.sample_view import SamplePosition


class RobotArm(BaseDevice):
    description: ClassVar[str] = "Fake robot arm"

    def __init__(self, *args, **kwargs):
        """Initialize the RobotArmCharacterization object."""
        super().__init__(*args, **kwargs)  # noqa: B904
        self._is_running = False

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
        self._is_running = True

        def finish():
            self._is_running = False

        t = Timer(0.1, finish)
        t.start()

    def get_most_recent_picture_location(self):
        # Return the path to large_file_example.zip relative to this file
        return Path(__file__).parent.parent / "large_file_example.zip"

    def is_running(self) -> bool:
        return self._is_running

    def connect(self):
        pass

    def disconnect(self):
        pass
