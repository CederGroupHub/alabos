from typing import ClassVar

from alab_management import BaseDevice, SamplePosition


class RobotArm(BaseDevice):
    description: ClassVar[str] = "Fake robot arm"

    @property
    def sample_positions(self):
        return [
            SamplePosition(
                "{name}/sample_holder".format(name=self.name),
                description="The position that can hold the sample",
            ),
        ]

    def emergent_stop(self):
        pass

    def run_program(self, program):
        pass

    def is_running(self) -> bool:
        return False

    def connect(self):
        pass

    def disconnect(self):
        pass
