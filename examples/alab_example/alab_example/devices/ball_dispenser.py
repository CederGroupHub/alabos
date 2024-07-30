"""This module contains the BallDispenser class for dispensing milling balls into
crucibles or plastic vials for grinding powders.
"""

from typing import ClassVar

from alab_control.ball_dispenser import BallDispenser as BallDispenserDriver
from alab_control.ball_dispenser import EmptyError

from alab_management import BaseDevice, SamplePosition, mock


class BallDispenser(BaseDevice):
    """A device for dispensing milling balls into crucibles or plastic vials for grinding powders."""

    description: ClassVar[str] = (
        "Dispenses milling balls into crucibles or plastic vials for grinding powders."
    )

    def __init__(self, ip_address: str, port: int = 80, *args, **kwargs):
        """Initialize the BallDispenser object."""
        super().__init__(*args, **kwargs)
        # self._stock = initial_fill
        self.ip_address = ip_address
        self.port = port
        self.driver: BallDispenserDriver | None = None

    @mock(object_type=BallDispenserDriver)
    def get_driver(self):
        """Return the driver for the BallDispenser."""
        self.driver = BallDispenserDriver(ip_address=self.ip_address, port=self.port)
        return self.driver

    def connect(self):
        """Connect to the BallDispenser."""
        self.driver = self.get_driver()

    def disconnect(self):
        """Disconnect from the BallDispenser."""
        self.driver = None

    @property
    def sample_positions(self):
        """Return the sample positions of the BallDispenser."""
        return [
            SamplePosition(
                "slot",
                description="A slot for either a crucible or vial. Sample is placed here during dispensing.",
                number=1,
            )
        ]

    def dispense_one(self):
        """Dispense a single ball."""
        self.set_message("Dispensing ball...")
        try:
            self.driver.dispense_balls()  # this dispenses a single ball
        except EmptyError as e:
            raise EmptyError("Ball dispenser is empty.") from e
        self.set_message("")

    def request_refill(self):
        """Request a refill of milling balls."""
        self.set_message("Out of balls! Submitted maintenance request for refill.")
        reply = "Unsuccessful"
        while reply == "Unsuccessful":
            reply = self.request_maintenance(
                prompt=f"{self.name} is empty. Reload with milling balls.",
                options=["Success", "Unsuccessful"],
            )
        self.set_message("")

    @mock(return_constant=False)
    def is_running(self):
        """Return whether the BallDispenser is running."""
        return self.driver.is_running()
