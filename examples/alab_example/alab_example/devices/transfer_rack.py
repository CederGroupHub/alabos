"""This module contains the TransferRack class."""

from typing import ClassVar

from alab_management.device_view import BaseDevice
from alab_management.sample_view import SamplePosition


class TransferRack(BaseDevice):
    """A rack that can hold vials or crucible."""

    description: ClassVar[str] = (
        "A rack that can hold vials or crucible. The slots are arranged in a grid on a flat surface, and the robot has "
    )
    "to be told which position to retrieve an unused vial from."

    def __init__(self, num_slots: int, *args, **kwargs):
        """Initialize the TransferRack object. The rack is a device because it can be reached by multiple robot arms.

        Args:
            num_slots (int): Number of slots in the rack.
            args: Additional arguments to pass to the BaseDevice constructor.
            kwargs: Additional keyword arguments to pass to the BaseDevice constructor.
        """
        if num_slots <= 0:
            raise ValueError("Number of slots must be greater than 0")
        self.num_slots = num_slots
        super().__init__(*args, **kwargs)

    def connect(self):
        """Connect to the TransferRack."""

    def disconnect(self):
        """Disconnect from the TransferRack."""

    @property
    def sample_positions(self):
        """Return the sample positions of the TransferRack."""
        return [
            SamplePosition(
                "slot",
                description=self.description,
                number=self.num_slots,
            ),
        ]

    def emergent_stop(self):
        """Stop the TransferRack."""
        return

    def is_running(self) -> bool:
        """Check if the TransferRack is running."""
        return False
