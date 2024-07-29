"""This module contains the code for controlling robot arm furnaces."""

import time

from alab_control.robot_arm_ur5e.robots import BaseURRobot
from alab_control.robot_arm_ur5e.ur_robot_dashboard import URRobotError
from alab_management.device_view import BaseDevice
from alab_management.device_view.device import mock
from alab_management.sample_view import SamplePosition
from alab_management.user_input import request_user_input


def sampleposition_to_waypoint(sample_position: str) -> str:
    """Convert a sample position to a waypoint name."""
    # TODO this is totally a hack to work with the initial waypoint names. eventually we will match waypoint names to
    # sample_position names
    prefix = sample_position.split(SamplePosition.SEPARATOR)[0]
    if prefix.startswith("box_"):
        prefix = "loading_rack"  # all box furnaces have crucible transfers in the loading_rack position
    index = sample_position.split(SamplePosition.SEPARATOR)[-1]
    return prefix + "/" + index


box_furnace_key = {
    "box_a": {
        "inside": ["Pick_BFRACK_1.urp", "Place_BF_A.urp"],
        "outside": ["Pick_BF_A.urp", "Place_BFRACK_1.urp"],
        "open_door": "",
        "close_door": "",
    },
    "box_b": {
        "inside": ["Pick_BFRACK_2.urp", "Place_BF_B.urp"],
        "outside": ["Pick_BF_B.urp", "Place_BFRACK_2.urp"],
        "open_door": "",
        "close_door": "",
    },
    "box_c": {
        "inside": ["Pick_BFRACK_3.urp", "Place_BF_C.urp"],
        "outside": ["Pick_BF_C.urp", "Place_BFRACK_3.urp"],
        "open_door": ["OpenDoor_C.urp"],
        "close_door": ["CloseDoor_C.urp"],
    },
    "box_d": {
        "inside": ["Pick_BFRACK_4.urp", "Place_BF_D.urp"],
        "outside": ["Pick_BF_D.urp", "Place_BFRACK_4.urp"],
        "open_door": "",
        "close_door": "",
    },
}


class RobotArmFurnaces(BaseDevice):
    """A device for controlling the UR5e robot arm."""

    description: str = "UR5e robot arm"

    def __init__(self, ip: str, *args, **kwargs):
        """Initialize the RobotArmFurnaces object."""
        super().__init__(*args, **kwargs)
        self.ip = ip
        self.driver = None
        self.context = "crucible"

    @mock(object_type=BaseURRobot)
    def get_driver(self):
        """Return the driver for the RobotArmFurnaces."""
        self.driver = BaseURRobot(self.ip)
        self.driver.set_speed(0.8)
        self._confirm_connection_in_remote_mode()
        return self.driver

    def connect(self):
        """Connect to the RobotArmFurnaces."""
        self.driver = self.get_driver()

    def disconnect(self):
        """Disconnect from the RobotArmFurnaces."""
        if self.driver is not None:
            self.driver.close()

    def _confirm_connection_in_remote_mode(self):
        if self.driver is None:
            raise Exception("Device is not connected!")
        while not self.driver.is_remote_mode():
            self._device_view.pause_device(self.name)
            self.set_message(
                "The arm is not under remote control. Please set to remote control and try again."
            )
            self.request_maintenance(
                prompt=f"Please set {self.name} to remote control, then press OK to continue.",
                options=["OK"],
            )
            if self.driver.is_remote_mode():
                self._device_view.unpause_device(self.name)
                self.set_message(
                    f"Successfully connected to {self.name} in remote control mode!"
                )

    @property
    def sample_positions(self):
        """Return the sample positions of the RobotArmFurnaces."""
        return [
            SamplePosition(
                "gripper",
                description="The gripper at the end of the robot arm. This clasps samples for movements.",
            ),
        ]

    def emergent_stop(self):
        """Stop the RobotArmFurnaces."""
        self.driver.stop()

    @mock(return_constant=False)
    def is_running(self):
        """Return whether the RobotArmFurnaces is running."""
        for i in range(4):
            try:
                return self.driver.is_running()
            except (URRobotError, ConnectionError):
                if i == 3:
                    raise

                if i != 0:
                    response = request_user_input(
                        task_id=None,
                        prompt="Set the robot arm to remote mode and try again.",
                        options=["Retry", "Cancel"],
                        maintenance=True,
                    )
                    if response == "Cancel":
                        raise

                self.disconnect()
                self.connect()
        return None

    def wait_for_finish(self):
        """Wait for the robot arm to finish."""
        while self.is_running():
            time.sleep(0.5)

    def run_program(self, program, block: bool = True):
        """Run a program on the robot arm."""
        # check if the robot arm can be connected
        self.is_running()

        for i in range(3):
            try:
                self.driver.run_program(program, block=block)
            except URRobotError as exc:
                if i == 2:
                    raise
                if "Failed to execute: play" in exc.args[0]:
                    response = request_user_input(
                        task_id=None,
                        prompt=f"Set the robot arm to the starting position of {program} and try again.",
                        options=["Retry", "Cancel"],
                        maintenance=True,
                    )
                    if response == "Cancel":
                        raise

                elif "reconnect to port 29999" in exc.args[0]:
                    if i != 0:
                        response = request_user_input(
                            task_id=None,
                            prompt=f"Set the robot arm to the starting position of {program} and try again.",
                            options=["Retry", "Cancel"],
                            maintenance=True,
                        )
                        if response == "Cancel":
                            raise

                    self.disconnect()
                    self.connect()
                else:
                    raise
            else:
                break

    def run_programs(self, programs, block: bool = True):
        """Run a list of programs on the robot arm."""
        for p in programs:
            self.run_program(p, block=block)

    def move_rack_into_box_furnace(self, box_furnace_name: str):
        """Move the rack into the box furnace."""
        program_dict = box_furnace_key.get(box_furnace_name)
        if program_dict is None:
            raise ValueError(
                f"No program found for box furnace by name {box_furnace_name}"
            )
        self.set_message(f"Putting rack inside box furnace {box_furnace_name}")
        self.driver.run_programs(program_dict["inside"])

    def take_rack_out_of_box_furnace(self, box_furnace_name: str):
        """Take the rack out of the box furnace."""
        program_dict = box_furnace_key.get(box_furnace_name)
        if program_dict is None:
            raise ValueError(
                f"No program found for box furnace by name {box_furnace_name}"
            )
        self.set_message(f"Taking rack out of box furnace {box_furnace_name}")
        self.driver.run_programs(program_dict["outside"])

    def open_box_furnace(self, box_furnace_name: str):
        """Open the box furnace door."""
        if box_furnace_name not in box_furnace_key:
            raise ValueError(
                f'No rack positions defined for box furnace name "{box_furnace_name}"'
            )
        if box_furnace_key[box_furnace_name]["open_door"] == "":
            raise ValueError(
                f'No open door program defined for box furnace name "{box_furnace_name}"'
            )

        programs = box_furnace_key[box_furnace_name]["open_door"]

        self.set_message(f'Opening box furnace "{box_furnace_name}"')
        self.driver.run_programs(programs)
        self.set_message("")

    def close_box_furnace(self, box_furnace_name: str):
        """Close the box furnace door."""
        if box_furnace_name not in box_furnace_key:
            raise ValueError(
                f'No rack positions defined for box furnace name "{box_furnace_name}"'
            )
        if box_furnace_key[box_furnace_name]["close_door"] == "":
            raise ValueError(
                f'No close door program defined for box furnace name "{box_furnace_name}"'
            )

        programs = box_furnace_key[box_furnace_name]["close_door"]

        self.set_message(f'Closing box furnace "{box_furnace_name}"')
        self.driver.run_programs(programs)
        self.set_message("")

    def download_folder(
        self,
        remote_folder_path: str,
        local_folder_path: str,
        remove_remote_files: bool = False,
    ):
        """
        Download files in a folder from the robot arm if they are not in the local folder.
        Remove files from the remote folder if remove_remote_files is True.
        """
        self.driver.ssh.download_folder(
            remote_folder_path, local_folder_path, remove_remote_files
        )
