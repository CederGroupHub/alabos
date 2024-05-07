from typing import ClassVar

from alab_management.device_view import BaseDevice
from alab_management.sample_view import SamplePosition


class DeviceThatNeverEnds(BaseDevice):
    """
    This is a fake device that never ends. This is used for testing the cancel feature.
    """

    description: ClassVar[str] = "DeviceThatNeverEnds"

    @property
    def sample_positions(self):
        return [
            SamplePosition(
                "infinite_loop",
                description="This is a fake device that never ends.",
            ),
        ]

    def emergent_stop(self):
        pass

    def run_infinite(self):
        while True:
            pass

    def connect(self):
        pass

    def disconnect(self):
        pass

    def is_running(self) -> bool:
        return False
