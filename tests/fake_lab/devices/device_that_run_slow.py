from typing import ClassVar

from alab_management.device_view import BaseDevice
from alab_management.sample_view import SamplePosition


class DeviceThatRunSlow(BaseDevice):
    description: ClassVar[str] = "DeviceThatRunsSlow"

    @property
    def sample_positions(self):
        return [
            SamplePosition(
                "slow",
                description="This is a fake device that runs slow.",
            ),
        ]

    def emergent_stop(self):
        pass

    def run_slow(self):
        import time

        time.sleep(100)

    def connect(self):
        pass

    def disconnect(self):
        pass

    def is_running(self) -> bool:
        return False
