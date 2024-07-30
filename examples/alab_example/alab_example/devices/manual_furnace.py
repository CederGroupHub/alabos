"""This module contains the ManualFurnace class."""

from typing import ClassVar

from alab_management.device_view import BaseDevice
from alab_management.sample_view import SamplePosition


class ManualFurnace(BaseDevice):
    """A device for controlling a manual furnace."""

    description: ClassVar[str] = "Manual furnace"

    def __init__(self, furnace_letter: str, *args, **kwargs):
        """Initialize the ManualFurnace object."""
        super().__init__(*args, **kwargs)
        self.furnace_letter = furnace_letter
        self._is_running = False

    def connect(self):
        """Connect to the ManualFurnace."""
        return

    def disconnect(self):
        """Disconnect from the ManualFurnace."""
        return

    @property
    def sample_positions(self):
        """Return the sample positions of the ManualFurnace."""
        return [
            SamplePosition(
                "slot",
                description="The position inside the box furnace, where the samples are heated",
                number=8,
            ),
        ]

    def start(self):
        """Start the ManualFurnace."""
        self._is_running = True

    def stop(self):
        """Stop the ManualFurnace."""
        self._is_running = False

    def emergent_stop(self):
        """Emergency stop the ManualFurnace."""
        self._is_running = False

    def is_running(self) -> bool:
        """Return whether the ManualFurnace is running."""
        return self._is_running
