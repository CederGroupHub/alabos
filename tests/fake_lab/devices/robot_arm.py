from typing import ClassVar

from alab_management import BaseDevice, SamplePosition, add_device


class RobotArm(BaseDevice):
    description: ClassVar[str] = "Fake robot arm"

    @property
    def sample_positions(self):
        return [
            SamplePosition(
                "{name}/sample_holder".format(name=self.name),
                description="The position that can hold the sample"
            ),
        ]

    def emergent_stop(self):
        pass

    def run_program(self, program):
        pass

    def is_running(self) -> bool:
        return False


add_device(RobotArm(name="dummy"))
