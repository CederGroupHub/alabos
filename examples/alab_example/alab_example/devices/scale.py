"""This module contains the Scale class for weighing jars/crucibles on the characterization side of the ALab."""

from typing import ClassVar

from alab_control.ohaus_scale import OhausScale as ScaleDriver
from alab_management.device_view import BaseDevice
from alab_management.device_view.device import mock
from alab_management.sample_view import SamplePosition


class Scale(BaseDevice):
    """A device for weighing jars/crucibles on the characterization side of the ALab."""

    description: ClassVar[str] = "Ohaus scale for weighing jars/crucibles on the characterization side of the ALab."
    TIMEOUT: int = 15  # seconds to timeout if no response from scale

    def __init__(self, ip_address: str, *args, **kwargs):
        """Initialize the Scale object."""
        super().__init__(*args, **kwargs)
        self.ip_address = ip_address

    @mock(object_type=ScaleDriver)
    def get_driver(self):
        """Return the driver for the Scale."""
        self.driver = ScaleDriver(ip=self.ip_address, timeout=self.TIMEOUT)
        self.driver.set_unit_to_mg()
        return self.driver

    def connect(self):
        """Connect to the Scale."""
        self.driver = self.get_driver()

    def disconnect(self):
        """Disconnect from the Scale."""
        self.driver = None

    @mock(return_constant=100)
    def get_mass_in_mg(self) -> int:
        """Return the mass of the sample in milligrams."""
        return self.driver.get_mass_in_mg()

    @property
    def sample_positions(self):
        """Return the sample positions of the Scale."""
        return [
            SamplePosition(
                "slot",
                description="Slot that can accept one sample (in either a crucible or plastic vial). This is the "
                "center of the scale itself.",
            ),
        ]

    def emergent_stop(self):
        """Stop the Scale."""

    @mock(return_constant=False)
    def is_running(self) -> bool:
        """Return whether the Scale is running."""
        return False
