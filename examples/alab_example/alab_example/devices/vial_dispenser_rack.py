"""This module contains the VialState enumeration and related imports."""

import time
from enum import Enum
from threading import Thread
from typing import ClassVar

from alab_management.device_view import BaseDevice


class VialState(Enum):
    """Enumeration of the states of a vial."""

    EMPTY = "empty"
    AVAILABLE = "available"


class EmptyError(Exception):
    """no fresh vials available."""


class VialDispenserRack(BaseDevice):
    """A set of racks that can hold fresh vials. These are arranged in a grid on a flat surface, and the robot has
    to be told which position to retrieve an unused vial from.
    """

    description: ClassVar[str] = "A set of square-grid racks holding fresh vials."

    RACKS = ["A", "B"]
    NUM_SLOTS = 16
    REFILL_EVERY = 8  # number of vials to refill at a time, should be a factor of NUM_SLOTS

    SLOTS_PER_RACK = [str(i + 1) for i in range(NUM_SLOTS)]

    def __init__(self, *args, **kwargs):
        """Initialize the VialDispenserRack object."""
        super().__init__(*args, **kwargs)
        self.vial_status = self.dict_in_database(
            name="vial_status",
            default_value={
                f"{rack}{slot}": VialState.AVAILABLE.value for rack in self.RACKS for slot in self.SLOTS_PER_RACK
            },
        )  # assume fully stocked at startup
        self.refill_daemon_thread = None
        self._refill_daemon_running = False

    def connect(self):
        """Connect to the VialDispenserRack."""
        self.start_refill_daemon()

    def disconnect(self):
        """Disconnect from the VialDispenserRack."""
        self.stop_refill_daemon()

    def start_refill_daemon(self):
        """Start the refill daemon."""
        if self._refill_daemon_running:
            return

        self._refill_daemon_running = True  # must be set before starting the thread
        self.refill_daemon_thread = Thread(target=self.refill_daemon_routine)
        self.refill_daemon_thread.start()

    def stop_refill_daemon(self):
        """Stop the refill daemon."""
        if self._refill_daemon_running:
            self.refill_daemon_thread.join()
            self._refill_daemon_running = False

    def refill_daemon_routine(self):
        """Primary routine for the refill daemon."""
        while self._refill_daemon_running:
            for rack in self.RACKS:
                for i in range(0, self.NUM_SLOTS, self.REFILL_EVERY):
                    slot_keys = [f"{rack}{slot}" for slot in self.SLOTS_PER_RACK[i : i + self.REFILL_EVERY]]
                    if self._check_refill(slot_keys):
                        self._request_refill(slot_keys)  # daemon blocks until refilled  TODO: non-blocking
                    time.sleep(5)

    @property
    def sample_positions(self):
        """Return the sample positions of the VialDispenserRack."""
        return []

    def num_remaining(self):
        """Return the number of remaining vials."""
        return len([v for v in self.vial_status.values() if v == VialState.AVAILABLE.value])

    def emergent_stop(self):
        """Stop the VialDispenserRack."""
        return

    def is_running(self) -> bool:
        """Return whether the VialDispenserRack is running."""
        return False

    def get_vial(self) -> tuple[str, int]:
        """Returns the rack letter and slot number of the next available vial.

        Returns:
            Tuple[str, int]: rack letter (A,B) and slot number (1-16)
        """
        while True:
            try:
                rack, slot = self._get_vial_internal()
                return rack, slot
            except EmptyError:
                self.set_message("No vials left, waiting for vials to be refilled.")

    def consume_vial(self, rack: str, slot: int):
        """Mark a vial as consumed."""
        key = f"{rack}{slot}"
        if self.vial_status[key] == VialState.EMPTY.value:
            raise ValueError(f"Vial {rack}{slot} is already empty!")
        self.vial_status[key] = VialState.EMPTY.value

    def _get_vial_internal(self) -> tuple[str, int]:
        for rack in self.RACKS:
            for slot in self.SLOTS_PER_RACK:
                if self.vial_status[f"{rack}{slot}"] == VialState.AVAILABLE.value:
                    return rack, int(slot)
        raise EmptyError("No vials available")

    def _check_refill(self, slot_keys: list[str]) -> bool:
        return all(self.vial_status[key] != VialState.AVAILABLE.value for key in slot_keys)

    def _request_refill(self, slot_keys: list[str]):
        self.request_maintenance(
            prompt=f"Refill {self.REFILL_EVERY} fresh vials on Vial Dispenser Rack, "
            f"slots {slot_keys[0]}-{slot_keys[-1]}.",
            options=["Mark as Refilled"],
        )
        for key in slot_keys:
            self.vial_status[key] = VialState.AVAILABLE.value
