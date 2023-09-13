from typing import ClassVar
import time

from alab_control.robot_arm_ur5e import BaseURRobot

from alab_management import BaseDevice, SamplePosition


class RobotArm(BaseDevice):
    description: ClassVar[str] = "UR5e robot arm"

    def __init__(self, address: str, port: int = 29999, *args, **kwargs):
        super(RobotArm, self).__init__(*args, **kwargs)
        self.address = address
        self.port = port
        self.driver = URRobot(self.address, port=port)

    @property
    def sample_positions(self):
        return [
            SamplePosition(
                "{name}/sample_holder".format(name=self.name),
                description="The position that can hold the sample"
            ),
        ]

    def emergent_stop(self):
        self.driver.stop()

    def run_program(self, program):
        self.driver.run_program(program)
        time.sleep(2)
        self.driver.wait_for_finish()

    def is_running(self):
        return self.driver.is_running()
