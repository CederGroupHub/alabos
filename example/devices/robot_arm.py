from dataclasses import dataclass, field
from typing import ClassVar

from alab_management.device_def import BaseDevice
from alab_management.sample_position import SamplePosition


@dataclass
class RobotArm(BaseDevice):
    name: str
    address: str
    port: str = field(default=502)

    description: ClassVar[str] = "UR5e robot arm"

    def init(self):
        pass

    @property
    def sample_positions(self):
        return [
            SamplePosition(
                "{name}.sample_holder".format(name=self.name),
                description="The position that can hold the sample"
            ),
        ]
