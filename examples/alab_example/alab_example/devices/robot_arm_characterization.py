"""This module contains the code for robot arm characterization."""

import time

from alab_control.robot_arm_ur5e.robots import BaseURRobot
from alab_control.robot_arm_ur5e.ur_robot_dashboard import URRobotError
from alab_management.device_view import BaseDevice
from alab_management.device_view.device import mock
from alab_management.sample_view import SamplePosition
from alab_management.user_input import request_user_input


def sample_position_to_waypoint(sample_position: str) -> str:
    """Convert a sample position to a waypoint name."""
    # TODO this is totally a hack to work with the initial waypoint names. eventually we will match waypoint names to
    # sample_position names
    prefix = sample_position.split(SamplePosition.SEPARATOR)[0]
    if prefix.startswith("box_"):
        prefix = "loading_rack"  # all box furnaces have crucible transfers in the loading_rack position
    index = sample_position.split(SamplePosition.SEPARATOR)[-1]
    return prefix + "/" + index


pick_key = {
    "transfer_rack/slot": [
        "horizontal_to_vertical.urp",
        "pick_transfer_rack_1.auto.script",
    ],
    "vial_rack_b/1": ["horizontal_to_vertical.urp", "pick_vial_rack_b_1.auto.script"],
    "tube_furnace_3/slot": ["Pick_Crucible_TF0.urp"],
}

place_key = {
    "crucible_transfer_position": [
        "place_transfer_rack_B.auto.script",
        "horizontal_to_vertical.urp",
    ],
    "dumping_station": [
        "place_dumping_station.auto.script",
        "vertical_to_horizontal.urp",
    ],
}


class RobotArmCharacterization(BaseDevice):
    """A device for characterizing the UR5e robot arm."""

    description: str = "UR5e robot arm"

    def __init__(self, ip: str, *args, **kwargs):
        """Initialize the RobotArmCharacterization object."""
        super().__init__(*args, **kwargs)
        self.ip = ip
        self.driver: BaseURRobot = None

    @mock(object_type=BaseURRobot)
    def get_driver(self):
        """Return the driver for the RobotArmCharacterization."""
        self.driver = BaseURRobot(self.ip)
        self._confirm_connection_in_remote_mode()
        return self.driver

    def connect(self):
        """Connect to the RobotArmCharacterization."""
        self.driver = self.get_driver()

    def disconnect(self):
        """Disconnect from the RobotArmCharacterization."""
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
        """Return the sample positions of the RobotArmCharacterization."""
        return [
            SamplePosition(
                "gripper",
                description="The gripper at the end of the robot arm. This clasps samples for movements.",
            ),
        ]

    def emergent_stop(self):
        """Stop the RobotArmCharacterization."""
        self.driver.stop()

    @mock(return_constant=False)
    def is_running(self):
        """Return whether the RobotArmCharacterization is running."""
        for i in range(4):
            try:
                return self.driver.is_running()
            except (ConnectionError, URRobotError):
                if i == 3:
                    raise Exception  # TODO this raise statement is not tested
                if i != 0:
                    response = request_user_input(
                        task_id=None,
                        prompt="Set the robot arm to remote mode and try again.",
                        options=["Retry", "Cancel"],
                        maintenance=True,
                    )
                    if response == "Cancel":
                        raise Exception  # TODO this raise statement is not tested
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
        """Run multiple programs on the robot arm."""
        for p in programs:
            self.run_program(p, block=True)

    def move_sample(self, source, destination, block=True):
        """Move a sample from one position to another."""
        urps = pick_key[source] + place_key[destination]
        self.set_message(f"Moving sample from {source} to {destination}")
        self.run_programs(urps)
        self.set_message("")

    def clear_popup(self):
        """Clear the popup on the robot arm."""
        self.driver.clear_popup()

    @mock(return_constant='current_code="CH1032145"')
    def read_file(self, path: str):
        """Read a file from the robot arm."""
        return self.driver.ssh.read_file(path)

    @mock(return_constant=None)
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
