"""This module contains the Shaker class for controlling a vertical shaker."""

from typing import ClassVar

from alab_control.shaker import Shaker as ShakerDriver
from alab_management.device_view import BaseDevice
from alab_management.device_view.device import mock
from alab_management.sample_view import SamplePosition


class Shaker(BaseDevice):
    """A device for controlling a vertical shaker."""

    description: ClassVar[str] = "Vertical shaker for grinding powders in a crucible or plastic vial."

    def __init__(self, ip_address: str, port: int = 80, *args, **kwargs):
        """Initialize the Shaker object."""
        super().__init__(*args, **kwargs)
        self.ip_address = ip_address
        self.port = port
        self.driver: ShakerDriver = None

    @mock(object_type=ShakerDriver)
    def get_driver(self):
        """Return the driver for the Shaker."""
        self.driver = ShakerDriver(ip_address=self.ip_address, port=self.port)
        return self.driver

    def connect(self):
        """Connect to the Shaker."""
        self.driver = self.get_driver()

    def disconnect(self):
        """Disconnect from the Shaker."""
        self.driver = None

    @property
    def sample_positions(self):
        """Return the sample positions of the Shaker."""
        return [
            SamplePosition(
                "slot",
                description="Slot that can accept one sample (in either a crucible or plastic vial)",
            ),
        ]

    def emergent_stop(self):
        """Stop the Shaker."""
        if self.driver:
            self.driver.stop()

    def shake(self, duration_seconds: float, grab: bool = True):
        """Closes the vertical shaker to grab the sample, shakes it for the duration, then releases the shaker.

        Args:
            duration_seconds (float): seconds to shake
            grab (bool): whether to clamp (True) or not (False). Defaults to True.
        """
        if self.driver is None:
            raise ValueError("Driver not set. Cannot perform shake operation.")

        self.set_message(f"Shaking for {duration_seconds} seconds")
        if grab:
            self.driver.grab_and_shaking(duration_sec=duration_seconds)
        else:
            self.driver.shaking(duration_sec=duration_seconds)  # this is blocking
        self.set_message("")

    @mock(return_constant=False)
    def is_running(self) -> bool:
        """Return whether the Shaker is running."""
        if self.driver:
            return self.driver.is_running()

        raise Exception("Cannot check if shaker is running, not connected")

    def grab(self):
        """Close the grabber to hold the container."""
        self.driver.grab()

    def release(self):
        """Open the grabber to release the container."""
        self.driver.release()
