"""This module provides the TubeFurnace class for controlling a tube furnace device."""

from __future__ import annotations

from http.client import ImproperConnectionState
from typing import Literal
from xmlrpc.client import ServerProxy

from alab_control.tube_furnace_mti import TubeFurnace as TubeFurnaceDriver

from alab_management.device_view import BaseDevice
from alab_management.device_view.device import mock
from alab_management.sample_view import SamplePosition


class TubeFurnace(BaseDevice):
    """A device for controlling a tube furnace."""

    description: str = "Tube furnace"
    DOOR_OPENING_TEMPERATURE: float = (
        100  # temp must be at or below this value before the door will open
    )

    def __init__(self, furnace_index, *args, **kwargs):
        """Initialize the TubeFurnace object."""
        super().__init__(*args, **kwargs)
        self.furnace_index = furnace_index
        self.driver = None

    @mock(object_type=TubeFurnaceDriver)
    def get_driver(self):
        """Return the driver for the TubeFurnace."""
        # self.driver = TubeFurnaceDriver(furnace_index=self.furnace_index)
        address = f"http://192.168.0.11:400{self.furnace_index}"
        self.driver: TubeFurnaceDriver = ServerProxy(address)  # noqa
        return self.driver

    def connect(self):
        """Connect to the TubeFurnace."""
        self.driver = self.get_driver()

    def disconnect(self):
        """Disconnect from the TubeFurnace."""
        if self.driver is not None:
            self.driver.close()

    def emergent_stop(self):
        """Stop the TubeFurnace."""
        if self.driver is not None:
            self.driver.stop()

    @mock(return_constant=300)
    def get_temperature(self) -> float:
        """Returns the current temperature of the tube furnace."""
        # return self.driver.get_PV()
        return self._handle_error(self.driver.get_PV)

    @property
    def sample_positions(self):
        """Return the sample positions of the TubeFurnace."""
        return [
            SamplePosition(
                "slot",
                description="The position inside the tube furnace, where the samples are heated",
                number=4,
            ),
        ]

    @mock(return_constant=False)
    def is_running(self) -> bool:
        """Returns True if the tube furnace is running, False otherwise."""
        return self._handle_error(self.driver.is_running)

    def _handle_error(self, func, *args, **kwargs):
        while True:
            try:
                return func(*args, **kwargs)
            except TimeoutError:
                reponse = self.request_maintenance(
                    "The tube furnace is not responding. Please check the connection.",
                    ["Retry", "Cancel"],
                )
                if reponse == "Cancel":
                    raise
            except ImproperConnectionState:
                continue

    def open_door(self):
        """Opens the door of the tube furnace."""
        # if not self.driver.flange_state:
        self.set_message("Opening door...")
        # self.driver.open_door()  # TODO this doesnt block while door is opening
        self._handle_error(self.driver.open_door)
        self.set_message("Door is now open.")

    def close_door(self):
        """Closes the door of the tube furnace."""
        if self.driver.flange_state:
            self.set_message("Closing door...")
            # self.driver.close_door()  # TODO this doesnt block while door is closing
            self._handle_error(self.driver.close_door)
        self.set_message("Door is now closed.")

    def run_program(
        self,
        setpoints: list[list[float]],
        atmosphere: Literal["Ar", "O2", "2H_98Ar"],
        flow_rate_ccm: float | None = 100,
        cleaning_cycles: int | None = 3,
    ):
        """Runs a program in the tube furnace.

        Args:
            setpoints (List[List[float]]): A list of setpoints, where each setpoint is a list of two floats: [duration,
                temperature].
            atmosphere (Literal["Ar", "O2", "2H_98Ar"]): The atmosphere in the tube furnace.
            flow_rate_ccm (Optional[float], optional): The flow rate in ccm. Defaults to 100.
            cleaning_cycles (Optional[int], optional): The number of cleaning cycles. Defaults to 3.


        """
        # TODO: Add control code to the gas flow valve
        # TODO: do we need to control the gas flow valve?
        heating_profile = {
            "C01": 0,
        }
        if len(setpoints) >= 10:
            raise ValueError(
                "Too many setpoints. Max 10."
            )  # TODO is max 10 or 11? if 10, we should limit the program
            # to 9 to leave room for the final cooldown step.

        for i, (duration, temperature) in enumerate(setpoints):
            heating_profile[f"T{i + 1:02d}"] = duration
            heating_profile[f"C{i + 2:02d}"] = temperature
            if i == len(setpoints) - 1:
                heating_profile[f"T{i + 2:02d}"] = -121

        self.set_message(
            f"Running program with setpoints: {setpoints} in atmosphere: {atmosphere}"
        )
        self.driver.write_heating_profile(heating_profile)
        self.driver.set_cleaning_cycles(cleaning_cycles)
        self.driver.set_door_opening_temperature(self.DOOR_OPENING_TEMPERATURE)
        self.driver.set_automatic_flow_rate(flow_rate_ccm)
        self.driver.start_program()
