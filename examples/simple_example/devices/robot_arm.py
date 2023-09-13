"""A robot arm that can move the sample holder."""

import time
from typing import ClassVar

from alab_control.robot_arm_ur5e import URRobotSecondary

from alab_management import BaseDevice, SamplePosition


class RobotArm(BaseDevice):
    """A robot arm that can move the sample holder."""

    description: ClassVar[str] = "UR5e robot arm"

    def __init__(self, address: str, port: int = 29999, *args, **kwargs):
        """Initialize the robot arm.

        Args:
            address: the ip address of the robot arm
            port: the port of the robot arm.
        """
        super().__init__(*args, **kwargs)
        self.address = address
        self.port = port
        self.driver = URRobotSecondary(self.address, port=port)

    @property
    def sample_positions(self):
        """The sample positions that the robot arm can move to."""
        return [
            SamplePosition(
                f"{self.name}/sample_holder",
                description="The position that can hold the sample",
            ),
        ]

    def emergent_stop(self):
        """Stop the robot arm."""
        self.driver.stop()

    def run_program(self, program):
        """Run a program on the robot arm."""
        self.driver.run_program(program)
        time.sleep(2)
        self.driver.wait_for_finish()

    def is_running(self):
        """Check if the robot arm is running."""
        return self.driver.is_running()
