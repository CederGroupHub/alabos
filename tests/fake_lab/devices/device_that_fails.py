from typing import ClassVar

from alab_management.device_view import BaseDevice
from alab_management.sample_view import SamplePosition


class DeviceThatFails(BaseDevice):
    description: ClassVar[str] = "DeviceThatFails"

    @property
    def sample_positions(self):
        return [
            SamplePosition(
                "failures",
                description="This is a fake device that always fails.",
            ),
        ]

    def emergent_stop(self):
        pass

    def fail(self):
        raise ValueError("This device always fails.")

    def connect(self):
        pass

    def disconnect(self):
        pass

    def is_running(self) -> bool:
        return False