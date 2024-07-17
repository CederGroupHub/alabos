"""This module contains the HeatingWithAtmosphere task."""

from __future__ import annotations

import time
from typing import TYPE_CHECKING, Any, Literal

from alab_example.devices.robot_arm_furnaces import RobotArmFurnaces
from alab_example.devices.tube_furnace import TubeFurnace
from pydantic import BaseModel, Extra, Field, ValidationError

from alab_management import BaseTask
from alab_management.device_view.device import mock
from alab_management.task_view.task_enums import TaskPriority

from .moving import Moving

if TYPE_CHECKING:
    from alab_example.devices.labman_quadrant import LabmanQuadrant


class TemperatureLog(BaseModel, extra=Extra.forbid):
    """Temperature log of a sample during the heating process."""

    time_minutes: list[float] | None = Field(
        default=None,
        description="Time elapsed in minutes since the start of the heating process.",
    )
    temperature_celsius: list[float] | None = Field(
        default=None,
        description="Temperature of the sample in Celsius.",
    )


class HeatingResult(BaseModel, extra=Extra.forbid):
    """Heating task result."""

    setpoints: list[list[float]] | None = Field(
        default=None,
        description="List of setpoints in the form [[duration (minutes), target temperature (C)],...].",
    )
    atmosphere: Literal["Ar", "O2", "2H_98Ar"] | None = Field(
        default=None,
        description="Gas environment used to heat the samples.",
    )

    flow_rate: float | None = Field(
        default=None,
        description="Flow rate (cc/min) of the gas.",
    )

    purging_cycles: int | None = Field(
        default=None,
        description="Number of purging cycles.",
    )

    temperature_log: TemperatureLog | None = Field(
        default=None,
        description="Temperature log of the samples during the heating process.",
    )


class HeatingWithAtmosphere(BaseTask):
    """Heats up to four samples in a tube furnace with a specified gas atmosphere and flow rate."""

    LOGGING_INTERVAL_SECONDS = 30  # temperature logging frequency
    COOLDOWN_TIME_MINUTES = 10  # minutes to wait between opening the furnace
    # -> crucibles being cooled down so the robot arm can pick them up. #TODO
    MAX_TEMPERATURE = 1500
    """
    Setpoints example (Usually heating rate is <15 C/min):
    [[duration (minutes), temperature (C)],[duration (minutes), temperature (C)]]
    """

    def __init__(
        self,
        setpoints: list[list[float]],
        atmosphere: Literal["Ar", "O2", "2H_98Ar"],
        flow_rate: float,
        purging_cycles: int = 3,
        *args: Any,
        **kwargs: Any,
    ) -> None:
        """Heats up to four samples in a tube furnace with a specified gas atmosphere and flow rate.

        Args:
            setpoints (List[List[float]]): List of setpoints in the form [[duration (minutes), temperature (C)],[time
                (minutes), temperature (C)]]. These will be the vertices of the temperature profile.
            atmosphere (Literal[&quot;Ar&quot;, &quot;O2&quot;, &quot;2H_98Ar&quot;]): Gas environment to heat the
                samples in. Note that (for now) these gases must be set manually using valves on the back wall
                in 30-105. Example for a [10C/min ramp to 1000C, 5C/min ramp to 1500C, hold at 1500C for 10 minutes,
                cool down to 100C at 10C/min]: setpoints = [[100, 1000], [100, 1500], [10, 1500], [140, 100]]
            flow_rate (float): Flow rate (cc/min) of the gas. This is set automatically by the tube furnace.
            purging_cycles (int, optional): Number of purging cycles. Defaults to 3.
            args (Any): Additional arguments.
            kwargs (Any): Additional keyword arguments.
        """
        priority = kwargs.pop("priority", TaskPriority.NORMAL)
        super().__init__(priority=priority, *args, **kwargs)  # noqa
        self.num_samples = len(self.samples)
        self.setpoints = setpoints
        self.atmosphere = atmosphere
        self.flow_rate = flow_rate
        self.purging_cycles = purging_cycles

    def validate(self):
        """Validate the HeatingWithAtmosphere task."""
        if not 0 < len(self.samples) <= 4:
            raise ValueError("Number of samples must be between 1 and 4.")

        max_temperature = max(
            [temperature for (duration, temperature) in self.setpoints]
        )
        if max_temperature > self.MAX_TEMPERATURE:
            raise ValueError(
                f"Max temperature ({max_temperature}) must be less than {self.MAX_TEMPERATURE} C!"
            )
        return True

    def check_for_labman_quadrant(self) -> str | None:
        """Checks if any samples need to be moved away from a labman quadrant. returns the name of the LabmanQuadrant
        device to be reserved if necessary.

        Returns
        -------
            str: device name to reserve, or None
        """
        quadrant_names = set()
        for sample_name in self.samples:
            sample = self.lab_view.get_sample(sample_name)
            device_containing_sample = (
                self.lab_view.get_sample_position_parent_device(sample.position) or ""
            )  # if None, give an empty string
            if device_containing_sample.startswith("labmanquadrant"):
                quadrant_names.add(device_containing_sample)

        if len(quadrant_names) == 0:
            return None
        if len(quadrant_names) == 1:
            return quadrant_names.pop()
        raise ValueError(
            f"Samples are spread between {quadrant_names}. They must be in the same labman quadrant!"
        )
        # TODO support pulling from multiple quadrants

    @mock(return_constant=None)
    def cooldown(self):
        """Waits for the samples to cool down with the door open."""
        self.set_message(
            f"Letting samples cool off with the door open. {self.COOLDOWN_TIME_MINUTES} minutes remaining."
        )
        t0 = time.time()
        time_remaining = self.COOLDOWN_TIME_MINUTES - ((time.time() - t0) / 60)
        while time_remaining > 0:
            self.set_message(
                f"Letting samples cool off with the door open. {time_remaining:.1f} minutes remaining."
            )
            time.sleep(self.COOLDOWN_TIME_MINUTES * 5)
            time_remaining = self.COOLDOWN_TIME_MINUTES - ((time.time() - t0) / 60)

        self.set_message("Samples have cooled off and are ready to be handled.")

    def run(self):
        """Run the HeatingWithAtmosphere task."""
        self.set_message("Waiting for a tube furnace to become available.")
        with self.lab_view.request_resources({TubeFurnace: {"slot": 4}}) as (
            devices,
            sample_positions,
        ):
            furnace: TubeFurnace = devices[TubeFurnace]

            self.set_message(f"Opening {furnace.name}.")
            furnace.open_door()

            ### Move samples into the tube furnace
            resource_request = {RobotArmFurnaces: {}}
            labman_quadrant = self.check_for_labman_quadrant()
            reserving_labman_quadrant = labman_quadrant is not None
            if reserving_labman_quadrant:
                resource_request[labman_quadrant] = {}

            with self.lab_view.request_resources(resource_request) as (
                arm_devices,
                _,
            ):
                if reserving_labman_quadrant:
                    quadrant: LabmanQuadrant = arm_devices[labman_quadrant]
                    self.set_message(
                        f"Taking control of {labman_quadrant} to retrieve crucibles."
                    )
                    quadrant.take_control()
                for i, (sample, destination) in enumerate(
                    zip(
                        self.samples, sample_positions[TubeFurnace]["slot"], strict=True
                    )
                ):
                    self.set_message(
                        f"Moving {sample} to {destination}. ({i+1}/{self.num_samples})"
                    )
                    self.run_subtask(
                        Moving,
                        sample=sample,
                        destination=destination,
                    )
                if reserving_labman_quadrant:
                    self.set_message(f"Releasing control of {labman_quadrant}.")
                    quadrant.release_control()

            self.set_message(
                f"All samples loaded into {furnace.name}. Closing the door."
            )
            # furnace.close_door()  ## let the furnace close the door itself
            # run the furnace program + record temperature log.

            message_header = f"Profile: {self.setpoints}\nAtmosphere: {self.atmosphere}"

            self.set_message(message_header + "\nHeating...")
            furnace.run_program(
                setpoints=self.setpoints,
                atmosphere=self.atmosphere,
                flow_rate_ccm=self.flow_rate,
                cleaning_cycles=self.purging_cycles,
            )

            t0 = time.time()
            temperature_log = {"time_minutes": [], "temperature_celsius": []}
            while furnace.is_running():  # track from program start to cooldown
                current_temp = furnace.get_temperature()
                temperature_log["time_minutes"].append((time.time() - t0) / 60)
                temperature_log["temperature_celsius"].append(current_temp)
                # self.logger.log_device_signal(
                #     {
                #         "device": furnace.name,
                #         "temperature": current_temp,
                #     }
                # )
                time_elapsed_minutes = int((time.time() - t0) / 60)

                self.set_message(
                    f"{message_header}\nTemperature: {current_temp:.1f} C\n"
                    f"Time elapsed: {time_elapsed_minutes} minutes."
                )
                time.sleep(self.LOGGING_INTERVAL_SECONDS)
            furnace.set_message("Heating complete.")
            self.set_message("Furnace program finished, opening the door.")

            furnace.open_door()
            self.cooldown()
            with self.lab_view.request_resources(
                {
                    RobotArmFurnaces: {},
                    "transfer_rack": {"slot": self.num_samples},
                }
            ) as (inner_devices, inner_positions):
                furnace.open_door()

                destinations = inner_positions["transfer_rack"]["slot"]
                self.set_message(
                    f"Heating finished. Moving {sample} to {destination}. ({i+1}/{self.num_samples})"
                )
                for sample, destination in zip(
                    self.samples,
                    destinations,
                    strict=True,
                ):
                    self.run_subtask(
                        Moving,
                        sample=sample,
                        destination=destination,
                    )
            furnace.close_door()  # keep the furnace door closed

        heating_result = {
            "setpoints": self.setpoints,
            "atmosphere": self.atmosphere,
            "flow_rate": self.flow_rate,
            "purging_cycles": self.purging_cycles,
            "temperature_log": temperature_log,
        }
        try:
            HeatingResult(**heating_result)
        except ValidationError as e:
            self.set_message(
                "Error: The results do not match the HeatingResult schema. Please contact the developer."
            )
            raise e

        for sample in self.samples:
            # check if all the format is correct
            self.lab_view.update_sample_metadata(
                sample, {"heatingwithatmosphere_results": heating_result}
            )

        return heating_result
