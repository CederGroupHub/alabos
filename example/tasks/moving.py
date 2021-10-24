from dataclasses import dataclass, field

from alab_management.device_def import SamplePosition
from alab_management.op_def.base_operation import BaseOperation
from ..devices.robot_arm import RobotArm


@dataclass
class Moving(BaseOperation):
    src: SamplePosition
    dest: SamplePosition
    robot_arm: RobotArm = field(hash=False, compare=False)

    @property
    def operation_location(self):
        return self.src.name

    @property
    def dest_location(self):
        return self.dest.name

    @property
    def occupied_positions(self):
        return []

    def __call__(self):
        ...

    def is_running(self):
        ...
