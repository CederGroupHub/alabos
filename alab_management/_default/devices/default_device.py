from typing import ClassVar

from alab_management.device_view import BaseDevice
from alab_management.sample_view import SamplePosition


class DefaultDevice(BaseDevice):
    """Default device definition, refer to https://idocx.github.io/alab_management/device_definition.html. # TODO."""

    # You can add a description to the device.
    description: ClassVar[str] = "Default device"

    def __init__(self, ip_address: str, *args, **kwargs):
        """
        You can customize this method to store more information about the device. For example,
        if the device is communicated through a serial port, you can store the serial port information here.

        Args:
            ip_address: IP address of the device. This is just an example, you can change it to any other information.
            *args:
            **kwargs:
        """
        self.ip_address = ip_address
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
        """
        Connect to the device.

        In this method, you can define the connection to the device with various protocols. After calling
        this method, the instance should be able to communicate with the device.
        """
        pass

    def disconnect(self):
        """
        Disconnect from the device.

        In this method, you can define the disconnection from the device. Although the instance
        may still exist, it should not be able to communicate with the device after this method is called.
        """
        pass

    def is_running(self):
        """
        Check if the device is running.

        Returns
        -------
            bool: True if the device is running, False otherwise.
        """
        return False
