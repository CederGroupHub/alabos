"""This module contains the Heating task class."""

from __future__ import annotations

import time
from typing import TYPE_CHECKING

from alab_example.devices.box_furnace import BoxFurnace
from alab_example.devices.robot_arm_furnaces import RobotArmFurnaces
from pydantic import BaseModel, Extra, Field, ValidationError

from alab_management import BaseTask
from alab_management.device_view.device import mock
from alab_management.task_view.task_enums import TaskPriority
from alab_management.user_input import request_user_input

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

    heating_temperature: float | None = Field(
        default=None,
        description="Target temperature to which the samples were heated.",
    )
    heating_time: float | None = Field(
        default=None,
        description="Duration for which the samples were heated.",
    )
    heating_profiles: list[list] | None = Field(
        default=None,
        description="Heating profiles used to heat the samples.",
    )
    cooling_rate: float | None = Field(
        default=None,
        description="Rate at which the samples were cooled after heating.",
    )
    low_temperature_calcination: bool | None = Field(
        default=None,
        description="Whether the samples underwent low temperature calcination.",
    )
    temperature_log: TemperatureLog | None = Field(
        default=None,
        description="Temperature log of the samples during the heating process.",
    )


class Heating(BaseTask):
    """Heating task. Heats samples in a box furnace, in an air environment."""

    LOGGING_INTERVAL_SECONDS = 60  # temperature logging frequency
    RACK_COOLING_TIME_MINUTES = (
        60  # minutes to wait before taking out the rack after furnace door opens
    )
    COOLDOWN_TIME_MINUTES = 10  # minutes to wait between rack on the aluminum table and crucibles being cooled down
    # so the robot arm can pick them up.
    SUB_SAMPLES_LENGTH = 4
    MAX_TEMPERATURE = 1100

    def __init__(
        self,
        heating_time: float | None = None,  # Set default value to None
        heating_temperature: float | None = None,
        low_temperature_calcination: bool = False,
        profiles: list[list] | None = None,
        cooling_rate: float | None = None,
        *args,
        **kwargs,
    ):
        """Heating task. Heats samples in a box furnace, in an air environment.
            Ramps slowly (2C/min) to 300C, then rapidly (15C/min) to the target temperature, holds for the specified
            time, then passively cools to near room temperature. Can hold up to eight samples at once.

        Args:
            heating_time (float): Duration (in minutes) to heat the samples for at the specified temperature.
            heating_temperature (float): Temperature (in C) to heat the samples to.
            low_temperature_calcination (bool, optional): If True, will add a 6 hour dwell at 300C on the initial ramp.
            Defaults to False.
            profiles (list[list], optional): List of profiles to run. Each profile is a list of three floats:
            [temperature, rate, dwelling time]. For example: [[1000, 5, 60], [1200, 5, 240]]. Defaults to None.
            cooling_rate (float, optional): Rate at which to cool the samples after heating. Defaults to None.
            args: Additional arguments.
            kwargs: Additional keyword arguments.
        """
        priority = kwargs.pop("priority", TaskPriority.HIGH)
        super().__init__(priority=priority, *args, **kwargs)  # noqa

        self.num_samples = len(self.samples)
        self.heating_time = heating_time
        self.heating_temperature = heating_temperature
        self.low_temperature_calcination = low_temperature_calcination
        self.profiles = profiles
        self.cooling_rate = cooling_rate

    def validate(self):
        """Validate the Heating task."""
        if not 0 < len(self.samples) <= 8:
            raise ValueError("Number of samples must be between 1 and 8")
        if self.heating_temperature > self.MAX_TEMPERATURE:
            raise ValueError(
                "Heating temperature ({self.heating_temperature}) must be less than {self.MAX_TEMPERATURE} C!"
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
    def cooldown(self, furnace: BoxFurnace, temperature_log: dict):
        """Waits for the rack to cool down to near room temperature."""
        t0 = time.time()
        time_elapsed_minutes = 0
        while time_elapsed_minutes < self.COOLDOWN_TIME_MINUTES:
            time_elapsed_minutes = int((time.time() - t0) / 60)
            current_temp = furnace.get_temperature()
            temperature_log["time_minutes"].append((time.time() - t0) / 60)
            temperature_log["temperature_celsius"].append(current_temp)
            message_header = (
                "Furnace is done. Waiting to cooldown to T=100 C with door open."
            )
            self.set_message(
                message_header
                + f"\nTemperature: {current_temp:.1f} C\nTime elapsed: {time_elapsed_minutes} minutes."
            )
            time.sleep(self.LOGGING_INTERVAL_SECONDS)
        return temperature_log

    def run(self):
        """Run the Heating task."""
        self.set_message("Waiting for a box furnace to become available.")
        with self.lab_view.request_resources({BoxFurnace: {"slot": 8}}) as (
            devices,
            sample_positions,
        ):
            furnace: BoxFurnace = devices[BoxFurnace]

            self.set_message(f"Reserved box furnace {furnace.name}")
            self.lab_view.update_result(
                name="furnace_name", value=furnace.name
            )  # record the furnace name to the task result

            resource_request = {RobotArmFurnaces: {}}

            labman_quadrant = self.check_for_labman_quadrant()
            reserving_labman_quadrant = labman_quadrant is not None
            if reserving_labman_quadrant:
                resource_request[labman_quadrant] = {}
            # load all samples into the box furnace
            with self.lab_view.request_resources(resource_request) as (
                arm_devices,
                _,
            ):
                robot_arm: RobotArmFurnaces = arm_devices[RobotArmFurnaces]

                if reserving_labman_quadrant:
                    quadrant: LabmanQuadrant = arm_devices[labman_quadrant]
                    self.set_message(
                        f"Taking control of {labman_quadrant} to retrieve crucibles."
                    )
                    quadrant.take_control()

                if furnace.name == "box_c" or furnace.name == "box_d":
                    with self.lab_view.request_resources({"transfer_rack": {}}) as (
                        _,
                        reserved_positions,
                    ):
                        # Filter out samples that are already in the box furnace rack
                        filtered_destinations = list(
                            sample_positions[BoxFurnace]["slot"]
                        )
                        filtered_samples = list(self.samples)
                        for sample in self.samples:
                            sample_entry = self.lab_view.get_sample(sample=sample)
                            if sample_entry.position in filtered_destinations:
                                filtered_samples.remove(sample)
                                filtered_destinations.remove(sample_entry.position)
                        for i, (sample, destination) in enumerate(
                            zip(filtered_samples, filtered_destinations, strict=True)
                        ):
                            self.set_message(
                                f"Moving {sample} to {destination}. ({i+1}/{self.num_samples}). Booked transfer_rack "
                                "for collision avoidance."
                            )
                            self.run_subtask(
                                Moving,
                                sample=sample,
                                destination=destination,
                            )
                        # TODO: Check if quadrant that is currently facing outside is the same as the quadrant that was
                        # booked before
                else:
                    # Filter out samples that are already in the box furnace rack
                    filtered_destinations = list(sample_positions[BoxFurnace]["slot"])
                    filtered_samples = list(self.samples)
                    for sample in self.samples:
                        sample_entry = self.lab_view.get_sample(sample=sample)
                        if sample_entry.position in filtered_destinations:
                            filtered_samples.remove(sample)
                            filtered_destinations.remove(sample_entry.position)
                    for i, (sample, destination) in enumerate(
                        zip(filtered_samples, filtered_destinations, strict=True)
                    ):
                        self.set_message(
                            f"Moving {sample} to {destination}. ({i+1}/{self.num_samples})"
                        )
                        self.run_subtask(
                            Moving,
                            sample=sample,
                            destination=destination,
                        )
                    # TODO: Check if quadrant that is currently facing outside is the same as the quadrant that was
                    # booked before
                if reserving_labman_quadrant:
                    self.set_message(f"Releasing control of {labman_quadrant}.")
                    quadrant.release_control()

                self.set_message(
                    "All samples loaded into the rack. Moving the rack into the box furnace."
                )
                try:
                    furnace.open_door()
                except Exception:
                    response = request_user_input(
                        task_id=self.task_id,
                        prompt=f"Failed to open the furnace {furnace.name} door. You have two choices: \n"
                        "(1) Please open it manually (or using door controller device if you are confident) and \n"
                        "click Continue. \n"
                        "(2) Abort the task.\n",
                        options=["Continue", "Abort"],
                    )
                    if response == "Abort":
                        raise TimeoutError("Abort by user.")  # noqa: B904

                robot_arm.move_rack_into_box_furnace(box_furnace_name=furnace.name)

                self.set_message("Rack is in the box furnace. Closing the door.")
                try:
                    furnace.close_door()
                except Exception:
                    response = self.lab_view.request_user_input(
                        prompt=f"Failed to close the furnace {furnace.name} door. You have two choices: \n"
                        "(1) Please close it manually (or using door controller device if you are confident) and \n"
                        "click Continue. \n"
                        "(2) Abort the task. \n",
                        options=["Continue", "Abort"],
                    )
                    if response == "Abort":
                        raise TimeoutError("Abort by user.")  # noqa: B904

            furnace.run_program(
                heating_time_minutes=self.heating_time,
                heating_temperature=self.heating_temperature,
                low_temperature_calcination=self.low_temperature_calcination,
                profiles=self.profiles,
                cooling_rate=self.cooling_rate,
            )
            t0 = time.time()
            temperature_log = {"time_minutes": [], "temperature_celsius": []}
            current_temp = 0
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
                if (
                    self.heating_time is not None
                    and self.heating_temperature is not None
                ):
                    message_header = f"Heating at {self.heating_temperature:.2f}C for {self.heating_time:.2f} minutes"
                    current_temp_num = (
                        float(current_temp)
                        if isinstance(current_temp, int | float)
                        else 0.0
                    )

                    self.set_message(
                        f"{message_header}\nTemperature: {current_temp_num:.1f} C\n"
                        "Time elapsed: {time_elapsed_minutes_num} minutes."
                    )

                elif self.profiles is not None:
                    temperatures = []
                    rates = []
                    dwellings = []
                    for profile in self.profiles:
                        temperatures.append(profile[0])
                        rates.append(profile[1])
                        dwellings.append(profile[2])
                    message_header = f"Heating at {temperatures!s} C for {dwellings!s} minutes using ramp rates {rates!s}"
                    self.set_message(
                        message_header
                        + f"Temperature: {current_temp:.1f} C\nTime elapsed: {time_elapsed_minutes} minutes."
                    )

                time.sleep(self.LOGGING_INTERVAL_SECONDS)
            furnace.set_message("")
            # If furnace name is box_b, do the classic way (open door after T=100 C and unload rack directly)
            # If furnace name is either of box_a,box_c,box_d do the new way (open door after T=300 C and unload rack
            # after RACK_COOLING_TIME_MINUTES to get T=100 C)
            # Take out crucible after COOLDOWN_TIME_MINUTES, counted from rack T=100 C
            # unload all samples from box furnace -> transfer rack

            if furnace.name == "box_b":
                while furnace.get_temperature() > 100.0:
                    current_temp = furnace.get_temperature()
                    temperature_log["time_minutes"].append((time.time() - t0) / 60)
                    temperature_log["temperature_celsius"].append(current_temp)
                    message_header = "Furnace is done. Waiting to cooldown to T=100 C with door closed."
                    self.set_message(
                        message_header
                        + f"\nTemperature: {current_temp:.1f} C\nTime elapsed: {time_elapsed_minutes} minutes."
                    )
                    time.sleep(self.LOGGING_INTERVAL_SECONDS)
                self.set_message(
                    f"Box furnace {furnace.name} is done. Requesting robot arm to unload rack."
                )
                with self.lab_view.request_resources({RobotArmFurnaces: {}}) as (
                    arm_devices,
                    _,
                ):
                    robot_arm: RobotArmFurnaces = arm_devices[RobotArmFurnaces]

                    self.set_message("Furnace is done. Opening the door.")
                    furnace.open_door()

                    self.set_message(
                        f"Taking the rack out of box furnace {furnace.name}"
                    )
                    robot_arm.take_rack_out_of_box_furnace(
                        box_furnace_name=furnace.name
                    )  # move rack to loading rack

                    self.set_message(f"Closing the door for box furnace {furnace.name}")
                    furnace.close_door()

            elif furnace.name in ["box_a", "box_c", "box_d"]:
                self.set_message(
                    "Furnace is done. Requesting robot arm to be idle before opening any door."
                )
                with self.lab_view.request_resources({RobotArmFurnaces: {}}) as (
                    arm_devices,
                    _,
                ):
                    robot_arm: RobotArmFurnaces = arm_devices[RobotArmFurnaces]
                    self.set_message(
                        "Furnace is done. Opening the door to cooldown to T=100 C."
                    )
                    furnace.open_door()
                temperature_log = self.cooldown(furnace, temperature_log)
                self.set_message(
                    f"Box furnace {furnace.name} is done. Requesting robot arm to unload rack."
                )
                with self.lab_view.request_resources({RobotArmFurnaces: {}}) as (
                    arm_devices,
                    _,
                ):
                    robot_arm: RobotArmFurnaces = arm_devices[RobotArmFurnaces]
                    self.set_message(
                        f"Taking the rack out of box furnace {furnace.name}"
                    )
                    robot_arm.take_rack_out_of_box_furnace(
                        box_furnace_name=furnace.name
                    )  # move rack to loading rack
                    self.set_message(f"Closing the door for box furnace {furnace.name}")
                    furnace.close_door()
            self.set_message(
                f"Samples are in the rack of {furnace.name} outside the oven. Waiting for samples to cool down."
            )

            self.set_message("Samples are cooled down. Heating task is finished")

        heating_result = {
            "heating_temperature": self.heating_temperature,
            "heating_time": self.heating_time,
            "heating_profiles": self.profiles,
            "cooling_rate": self.cooling_rate,
            "low_temperature_calcination": self.low_temperature_calcination,
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
                sample, {"heating_results": heating_result}
            )

        return heating_result
