import time
from datetime import timedelta
from typing import ClassVar

from alab_control.door_controller import DoorController
from alab_control.furnace_2416 import FurnaceController, Segment
from alab_control.furnace_2416.furnace_driver import (
    FurnaceError,
    ProgramEndType,
    SegmentType,
)

from alab_management import BaseDevice, SamplePosition, mock


class Boxfurnace(BaseDevice):
    description: ClassVar[str] = (
        "The box furnace is a device that can heat samples up to 1200 degrees Celsius. "
        "It is used for heat treatment of samples. In current setting, one box furnace "
        "can hold up to 8 samples. Due to the limitation of the power supply, the "
        "max ramping rate is 10 degrees Celsius per minute."
    )

    def __init__(self, com_port_id: str, *args, **kwargs):
        """
        You can customize this method to store more information about the device. For example,
        if the device is communicated through a serial port, you can store the serial port information here.

        Args:
            com_port_id: The ID of the COM port that the device is connected to.
        """
        self.com_port_id = com_port_id
        self.door_controller = DoorController(
            names=[self.name], ip_address="192.168.0.51"
        )
        self.driver = None
        super().__init__(*args, **kwargs)

    @property
    def sample_positions(self):
        """
        Return the sample positions of the BoxFurnace.

        Sample positions are the positions inside the device where the samples are placed.
        It is used to track the samples in the system. When setting up the system,
        all the sample positions will be created and stored in the database.
        """
        return [
            SamplePosition(
                "slot",
                description="The position inside the box furnace, where the samples are heated",
                number=8,
            ),
        ]

    @mock(
        object_type=FurnaceController
    )  # Mock the driver for testing. It will return a `unittest.mock.Mock` object.
    def get_driver(self):
        """Return the driver of the device."""
        return FurnaceController(port=self.com_port_id)

    def connect(self):
        """Connect to the BoxFurnace."""
        self.driver = self.get_driver()

    def disconnect(self):
        """Disconnect from the BoxFurnace."""
        if self.driver is not None:
            self.driver.close()
        self.driver = None

    @mock(return_constant=False)
    def is_running(self):
        """Check if the device is running."""
        return self.driver.is_running()

    def run_program(
        self,
        profiles: list[list[float]],
    ):
        """
        Run a heating program on the BoxFurnace.

        Args:
            profiles: A list of profiles. Each profile is a list of three elements:
                - The target temperature in Celsius.
                - The ramping rate in Celsius per minute.
                - The duration in minutes
        """
        segments = []
        for profile in profiles:
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

        segments = [
            *segments,
            Segment(segment_type=SegmentType.END, endt=ProgramEndType.RESET),
        ]
        self.set_message(
            "Running a program with profiles:\n"
            + "\n".join(
                [
                    f"Setpoint: {profile[0]} C, "
                    f"Ramp rate: {profile[1]} C/min, "
                    f"Dwelling duration: {profile[2]} min"
                    for profile in profiles
                ]
            )
        )

        while True:
            try:
                self.driver.run_program(*segments)
                time.sleep(2)
            except FurnaceError:  # if there is an error, prompt the user to retry
                response = self.request_maintenance(
                    prompt="There is an error running the program. Do you want to retry?",
                    options=["Yes", "No"],
                )
                if response == "No":
                    raise  # if the user chooses not to retry, raise the error
            else:
                break

    def open_door(self):
        """Open the door of the BoxFurnace."""
        self.door_controller.open(name=self.name)

    def close_door(self):
        """Close the door of the BoxFurnace."""
        self.door_controller.close(name=self.name)

    @mock(return_constant=30)
    def get_temperature(self):
        """Get the current temperature of the BoxFurnace."""
        return self.driver.get_temperature()
