"""This module contains the BoxFurnace class for controlling the Eurotherm 2416 Box Furnace."""

import time
from datetime import timedelta
from typing import ClassVar

from alab_control.door_controller import DoorController
from alab_control.furnace_2416 import FurnaceController, Segment
from alab_control.furnace_2416.furnace_driver import (
    ProgramEndType,
    SegmentType,
)

from alab_management.device_view import BaseDevice
from alab_management.device_view.device import log_signal, mock
from alab_management.sample_view import SamplePosition


class BoxFurnace(BaseDevice):
    """A device for controlling the Eurotherm 2416 Box Furnace."""

    description: ClassVar[str] = "Eurotherm 2416 Box Furnace"

    def __init__(
        self,
        com_port,
        door_controller: DoorController,
        furnace_letter: str,
        *args,
        **kwargs,
    ):
        """Initialize the BoxFurnace object."""
        super().__init__(*args, **kwargs)
        self.com_port = com_port
        self.driver = None
        self.door_controller = door_controller
        self.furnace_letter = furnace_letter

    @mock(object_type=[FurnaceController, DoorController])
    def get_driver(self):
        """Return the driver for the BoxFurnace."""
        self.driver = FurnaceController(port=self.com_port)
        return self.driver, self.door_controller

    def connect(self):
        """Connect to the BoxFurnace."""
        self.driver, self.door_controller = self.get_driver()

    def disconnect(self):
        """Disconnect from the BoxFurnace."""
        if self.driver is not None:
            self.driver.close()
        self.driver = None

    @property
    def sample_positions(self):
        """Return the sample positions of the BoxFurnace."""
        return [
            SamplePosition(
                "slot",
                description="The position inside the box furnace, where the samples are heated",
                number=8,
            ),
        ]

    def emergent_stop(self):
        """Stop the BoxFurnace."""
        self.driver.stop()

    def run_program(
        self,
        heating_time_minutes: float = None,
        heating_temperature: float = None,
        low_temperature_calcination: bool = False,
        profiles: list[list] = None,
        cooling_rate: float = None,
    ):
        """
        default template is used by filling in only heating_time_minutes and heating_temperature profiles is a list of
        [temperature, rate, dwelling time in minutes]. For example: [[1000, 5, 60], [1200, 5, 240]].
        """
        if profiles is None:
            if heating_temperature > 300:
                segments = [
                    Segment(
                        segment_type=SegmentType.RAMP_RATE,
                        target_setpoint=300,
                        ramp_rate_per_min=2,
                    ),
                ]
                if low_temperature_calcination:
                    segments = [
                        *segments,
                        Segment(
                            segment_type=SegmentType.DWELL,
                            duration=timedelta(minutes=60 * 6),
                        ),
                    ]
            else:
                segments = []

            segments = (
                segments
                + [
                    Segment(
                        segment_type=SegmentType.RAMP_RATE,
                        target_setpoint=heating_temperature,
                        ramp_rate_per_min=5,
                    )
                ]
                + [
                    Segment(
                        segment_type=SegmentType.DWELL,
                        # the upper limit of heating is 900 minutes
                        duration=timedelta(
                            minutes=(
                                900
                                if i < heating_time_minutes // 900
                                else heating_time_minutes % 900
                            )
                        ),
                    )
                    for i in range((heating_time_minutes + 899) // 900)
                ]
            )
            if cooling_rate is not None:
                segments = [
                    *segments,
                    Segment(
                        segment_type=SegmentType.RAMP_RATE,
                        target_setpoint=25,
                        ramp_rate_per_min=cooling_rate,
                    ),
                ]
                segments = [
                    *segments,
                    Segment(segment_type=SegmentType.END, endt=ProgramEndType.RESET),
                ]
            else:
                segments = [
                    *segments,
                    Segment(segment_type=SegmentType.END, endt=ProgramEndType.RESET),
                ]
            self.set_message(
                f"Heating at {heating_temperature} C for {heating_time_minutes} minutes"
            )
        else:
            temperatures = []
            rates = []
            dwellings = []
            segments = []
            for profile in profiles:
                temperatures.append(profile[0])
                rates.append(profile[1])
                dwellings.append(profile[2])
                segments.append(
                    Segment(
                        segment_type=SegmentType.RAMP_RATE,
                        target_setpoint=profile[0],
                        ramp_rate_per_min=profile[1],
                    )
                )
                segments = segments + [
                    Segment(
                        segment_type=SegmentType.DWELL,
                        # the upper limit of heating is 900 minutes
                        duration=timedelta(
                            minutes=900 if i < (profile[2] // 900) else profile[2] % 900
                        ),
                    )
                    for i in range((profile[2] + 899) // 900)
                ]
            if cooling_rate is not None:
                segments = [
                    *segments,
                    Segment(
                        segment_type=SegmentType.RAMP_RATE,
                        target_setpoint=25,
                        ramp_rate_per_min=cooling_rate,
                    ),
                ]
                segments = [
                    *segments,
                    Segment(segment_type=SegmentType.END, endt=ProgramEndType.RESET),
                ]
            else:
                segments = [
                    *segments,
                    Segment(segment_type=SegmentType.END, endt=ProgramEndType.RESET),
                ]
            self.set_message(
                f"Heating at {temperatures!s} C for {dwellings!s} minutes using ramp rates {rates!s}"
            )

        self.driver.run_program(*segments)
        time.sleep(2)

    @mock(return_constant=False)
    def is_running(self) -> bool:
        """
        Returns True if the box furnace is either:
            - currently running a program
            - too hot to be opened (ie still cooling down from a recently completed program).
        """
        return self.driver.is_running()

    @mock(return_constant=30)
    @log_signal("temperature", interval_seconds=60)
    def get_temperature(self) -> float:
        """Return the current temperature of the BoxFurnace."""
        return self.driver.current_temperature

    def open_door(self):
        """Open the door of the BoxFurnace."""
        self.door_controller.open(name=self.furnace_letter)

    def close_door(self):
        """Close the door of the BoxFurnace."""
        self.door_controller.close(name=self.furnace_letter)
