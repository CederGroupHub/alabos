"""This module contains the XRDDispenserRack class for managing the transfer rack for XRD sample holders."""

import time
from threading import Thread

from alab_management.device_view import BaseDevice
from alab_management.sample_view import SamplePosition, SampleView
from alab_management.user_input import UserInputView, UserRequestStatus


class XRDDispenserRack(BaseDevice):
    """A rack to hold clean and dirty sample holders for XRD."""

    description = "Transfer rack for XRD sample holders."
    num_slots = 16
    interval: float = 5

    def __init__(self, *args, **kwargs):
        """Initialize the XRDDispenserRack object."""
        super().__init__(*args, **kwargs)
        self._userinputview = UserInputView()
        self._sampleview = SampleView()
        self.available_slots = self.list_in_database(
            # "available_slots", [i + 1 for i in range(self.num_slots)]
            "available_slots",
            [1, 2, 3, 4, 5, 6, 7, 8, 10, 11, 12, 14, 15, 16],
        )
        self.dirty_slots = self.list_in_database("dirty_slots", [])
        self.pending_slotcleaning_requests = self.list_in_database(
            "pending_slotcleaning_requests", []
        )
        self.connected = False

    def connect(self):
        """Connect to the XRDDispenserRack."""
        self.connected = True
        self._update_thread = self._start_update_thread()

    def disconnect(self):
        """Disconnect from the XRDDispenserRack."""
        self.connected = False
        self._update_thread.join()

    def slot_to_sampleposition(self, slot: int):
        """Convert a slot number to a SamplePosition."""
        return f"{self.name}/slot/{slot}"

    def _start_update_thread(self):
        def update():
            while self.connected:
                to_be_removed = []
                for (
                    slot_idx,
                    userrequest_id,
                ) in self.pending_slotcleaning_requests:
                    request = self._userinputview.get_request(userrequest_id)
                    if (
                        UserRequestStatus(request["status"])
                        == UserRequestStatus.FULLFILLED
                    ):
                        self.mark_slot_available(slot_idx)
                        to_be_removed.append([slot_idx, userrequest_id])

                for entry in to_be_removed:
                    self.pending_slotcleaning_requests.remove(entry)

                time.sleep(self.interval)

        thread = Thread(target=update)
        thread.start()
        return thread

    @property
    def sample_positions(self):
        """Return the sample positions of the XRDDispenserRack."""
        return []

    def is_running(self) -> bool:
        """Return whether the XRDDispenserRack is running."""
        return False

    def emergent_stop(self):
        """Stop the XRDDispenserRack."""
        return

    def get_available_slot(self):
        """
        Blocks until a fresh XRD holder is available.

        Returns (slot number (int))
        """
        if len(self.available_slots) == 0:
            return None
        return self.available_slots.pop()

    def mark_slot_dirty(self, slot: int, sample_name: str, sample_position: str):
        """Mark a slot as dirty."""
        if slot in self.dirty_slots:
            return

        self.dirty_slots.append(slot)
        requestid = self._userinputview.insert_request(
            prompt=f"Clean the XRD sample holder in slot {slot} of {self.name}. Remove the sample {sample_name} on the "
            f"XRD holder or put the sample back into the vial at {sample_position} (might also be in the collective "
            "short-term storage)",
            options=["ok"],
            maintenance=True,
        )
        self.pending_slotcleaning_requests.append((slot, requestid))

    def mark_slot_available(self, slot: int):
        """Mark a slot as available."""
        if slot in self.available_slots:
            return
        self.dirty_slots.remove(slot)

        # if a sample was left on the XRD holder, consider it removed from the ALab.
        sample = self._sampleview._sample_collection.find_one(
            {"position": f"{self.name}/slot/{slot}"}
        )
        if sample is not None:
            self._sampleview.move_sample(sample_id=sample["_id"], position=None)

        self.available_slots.append(slot)

    def __del__(self):
        if self.connected:
            self.disconnect()
