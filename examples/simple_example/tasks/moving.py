from dataclasses import dataclass, field

from alab_management.op_def.base_operation import BaseMovingOperation
from alab_management.sample_position import SamplePosition, SamplePositionPair
from simple_example.devices.robot_arm import RobotArm


@dataclass
class Moving(BaseMovingOperation):
    src: SamplePosition
    dest: SamplePosition
    robot_arm: RobotArm = field(hash=False, compare=False)

    @staticmethod
    def get_possible_src_dest_pairs():
        return (
            SamplePositionPair("furnace_table", "furnace_1.inside", containers=["crucible"]),
            SamplePositionPair("furnace_table", "furnace_2.inside", containers=["crucible"]),
            SamplePositionPair("furnace_table", "furnace_3.inside", containers=["crucible"]),
            SamplePositionPair("furnace_table", "furnace_4.inside", containers=["crucible"]),
            SamplePositionPair("furnace_1.inside", "furnace_table"),
            SamplePositionPair("furnace_2.inside", "furnace_table"),
            SamplePositionPair("furnace_3.inside", "furnace_table"),
            SamplePositionPair("furnace_4.inside", "furnace_table"),
        )

    @property
    def operation_location(self):
        return self.src.name

    @property
    def dest_location(self):
        return self.dest.name

    @property
    def occupied_positions(self):
        return []

    def run(self, logger):
        ...

    def is_running(self):
        ...
