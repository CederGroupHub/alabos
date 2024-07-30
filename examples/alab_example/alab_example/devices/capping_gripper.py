"""This module contains the CappingGripper class for controlling a gripper that clamps a vial during capping."""

from typing import ClassVar

from alab_control.capper import Capper

from alab_management import BaseDevice, SamplePosition, mock


class CappingGripper(BaseDevice):
    """A gripper that clamps a vial during capping. This prevent the vial from rotating such that the cap can be
    tightenend/loosened.
    """

    description: ClassVar[str] = (
        "A gripper that clamps a vial during capping. This prevent the vial from rotating such that the cap can be "
    )
    "tightenend/loosened."

    def __init__(self, ip_address: str, port: int = 80, *args, **kwargs):
        """Initialize the CappingGripper object."""
        super().__init__(*args, **kwargs)
        self.ip_address = ip_address
        self.port = port

        self.driver: Capper | None = None

    @mock(object_type=Capper)
    def get_driver(self):
        """Return the driver for the CappingGripper."""
        self.driver = Capper(ip_address=self.ip_address, port=self.port)
        return self.driver

    def connect(self):
        """Connect to the CappingGripper."""
        self.driver = self.get_driver()

    def disconnect(self):
        """Disconnect from the CappingGripper."""
        self.driver = None

    def open(self):
        """Open the capping gripper."""
        self.set_message("Opening the capping gripper...")
        for i in range(3):
            try:
                self.driver.open()
            except Exception:  # noqa
                if i == 2:
                    raise
                response = self.request_maintenance(
                    prompt="Timeout in opening the capper. Check the capper and try again.",
                    options=["Retry", "Cancel"],
                )
                if response == "Cancel":
                    raise
            else:
                break
        self.set_message("Capping gripper is open.")

    def close(self):
        """Close the capping gripper."""
        self.set_message("Closing the capping gripper...")
        for i in range(3):
            try:
                self.driver.close()
            except Exception:  # noqa
                if i == 2:
                    raise
                response = self.request_maintenance(
                    prompt="Timeout in closing the capper. Check the capper and try again.",
                    options=["Retry", "Cancel"],
                )
                if response == "Cancel":
                    raise
            else:
                break
        self.set_message("Capping gripper is closed.")

    @property
    def sample_positions(self):
        """Return the sample positions of the CappingGripper."""
        return [
            SamplePosition(
                "slot",
                description="Slot that can accept one sample (in either a crucible or plastic vial). This is the "
                "capper position.",
            ),
        ]

    def emergent_stop(self):
        """Stop the CappingGripper."""

    @mock(return_constant=False)
    def is_running(self) -> bool:
        """Return whether the CappingGripper is running."""
        return False
