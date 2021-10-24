from dataclasses import dataclass, field

from alab_management.device_def import SamplePosition
from alab_management.op_def.base_operation import BaseMovingOperation
from devices.robot_arm import RobotArm


@dataclass
class Moving(BaseMovingOperation):
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

    @property
    def possible_src_dest(self):
        # in the future, this will be parsed from a file
        return [
            ("furnace_table", "furnace_1.inside"),
            ("furnace_table", "furnace_2.inside"),
            ("furnace_table", "furnace_3.inside"),
            ("furnace_table", "furnace_4.inside"),
            ("furnace_1.inside", "furnace_table"),
            ("furnace_2.inside", "furnace_table"),
            ("furnace_3.inside", "furnace_table"),
            ("furnace_4.inside", "furnace_table"),
        ]

    def __call__(self):
        ...

    def is_running(self):
        ...
