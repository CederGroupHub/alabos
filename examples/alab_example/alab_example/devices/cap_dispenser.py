"""This module provides the CapDispenser class for dispensing caps."""

import time
from typing import ClassVar

from alab_control.cap_dispenser import (
    CapDispenser as CapDispenserDriver,
)
from alab_control.cap_dispenser import (
    CapDispenserState,
)

from alab_management import BaseDevice, SamplePosition, mock


class CapDispenser(BaseDevice):
    """A device for dispensing caps."""

    description: ClassVar[str] = (
        "Dispenses up to four types of caps. For now, three are used: Normal lids for plastic vials, sieve lids for "
    )
    "plastic vials, and acrylic disks for powder flattening."
    SIEVE_CAP_INDEX = "B"
    NORMAL_CAP_INDEX = "A"
    ACRYLIC_DISK_INDEX = "C"

    STATE_UPDATE_INTERVAL = 2  # min seconds between updating state. basically a rate limiter to not overload the arduino

    def __init__(self, ip_address: str, port: int = 80, *args, **kwargs):
        """Initialize the CapDispenser object."""
        super().__init__(*args, **kwargs)
        # self._stock = initial_fill
        self.ip_address = ip_address
        self.port = port
        self.driver: CapDispenserDriver | None = None
        self.__last_state_update_time = time.time() - self.STATE_UPDATE_INTERVAL
        self.__last_state = None

    @mock(object_type=CapDispenserDriver)
    def get_driver(self):
        """Return the driver for the CapDispenser."""
        self.driver = CapDispenserDriver(ip_address=self.ip_address, port=self.port)
        return self.driver

    def connect(self):
        """Connect to the CapDispenser."""
        self.driver = self.get_driver()

    def disconnect(self):
        """Disconnect from the CapDispenser."""
        self.driver = None

    @property
    def sample_positions(self):
        """Return the sample positions of the CapDispenser."""
        return [
            SamplePosition(
                "normal_cap_slot",
                description="A slot to which normal vial caps are dispensed.",
                number=1,
            ),
            SamplePosition(
                "sieve_cap_slot",
                description="A slot to which sieve vial caps are dispensed.",
                number=1,
            ),
            SamplePosition(
                "acrylic_disk_slot",
                description="A slot to which acrylic disks for powder flattening are dispensed.",
                number=1,
            ),
        ]

    def open_normal_cap(self):
        """Open the normal cap dispenser."""
        self.set_message("Dispensing a normal cap...")
        self.driver.open(self.NORMAL_CAP_INDEX)
        self.set_message("Normal cap ready to be picked.")

    def close_normal_cap(self):
        """Close the normal cap dispenser."""
        self.set_message("Closing the normal cap dispenser...")
        self.driver.close(self.NORMAL_CAP_INDEX)
        self.set_message("Normal cap dispenser closed.")

    def open_sieve_cap(self):
        """Open the sieve cap dispenser."""
        self.set_message("Dispensing a sieve cap...")
        self.driver.open(self.SIEVE_CAP_INDEX)
        self.set_message("Sieve cap ready to be picked.")

    def close_sieve_cap(self):
        """Close the sieve cap dispenser."""
        self.set_message("Closing the sieve cap dispenser...")
        self.driver.close(self.SIEVE_CAP_INDEX)
        self.set_message("Sieve cap dispenser closed.")

    def open_acrylic_disk(self):
        """Open the acrylic disk dispenser."""
        self.set_message("Dispensing an acrylic disk...")
        self.driver.open(self.ACRYLIC_DISK_INDEX)
        self.set_message("Acrylic disk ready to be picked.")

    def close_acrylic_disk(self):
        """Close the acrylic disk dispenser."""
        self.set_message("Closing the acrylic disk dispenser...")
        self.driver.close(self.ACRYLIC_DISK_INDEX)
        self.set_message("Acrylic disk dispenser closed.")

    @mock(return_constant=False)
    def is_running(self) -> bool:
        """Has some rate limiting to not overload the arduino."""
        if time.time() - self.__last_state_update_time > self.STATE_UPDATE_INTERVAL:
            self.__last_state = self.driver.get_state() == CapDispenserState.RUNNING
            self.__last_state_update_time = time.time()
        return self.__last_state
