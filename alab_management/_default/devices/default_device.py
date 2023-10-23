from typing import ClassVar

from alab_management import BaseDevice, SamplePosition


class DefaultDevice(BaseDevice):
    """Default device definition, refer to https://idocx.github.io/alab_management/device_definition.html."""

    description: ClassVar[str] = "Default device"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    @property
    def sample_positions(self):
        """Sample positions define the sample positions related to this device."""
        return [
            SamplePosition(
                name="DefaultSamplePosition",
                number=4,
                description="Default sample position",
            )
        ]

    def connect(self):
        pass

    def disconnect(self):
        pass

    def emergent_stop(self):
        pass

    def is_running(self):
        return False


default_device_1 = DefaultDevice(name="default_device_1")
