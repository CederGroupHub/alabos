from bson import ObjectId
import time

from alab_management.task_view.task import BaseTask
from ..devices.robot_arm import RobotArm


class Moving(BaseTask):
    MOVING_URPS = {
        ("furnace_table", "ipad.inside"): ["weigh.urp"],
        ("ipad.inside", "furnace_table"): ["weigh2_11_15.urp"],
        ("furnace_table", "furnace.inside"): ["open_new_m.urp", "1-2.urp", "close_new_m.urp"],
        ("furnace.inside", "furnace_table"): ["open_new_m.urp", "2-1.urp", "close_new_m.urp"],
    }

    def __init__(self, sample: ObjectId, dest: str, *args, **kwargs):
        super(Moving, self).__init__(*args, **kwargs)
        self.sample = sample
        self.dest = dest

    def run(self):
        sample = self.lab_manager.get_sample(sample_id=self.sample)
        sample_position = sample.position

        with self.lab_manager.request_resources({RobotArm: [sample_position, self.dest]}) as \
                (devices, sample_positions):
            robot_arm: RobotArm = devices[RobotArm]
            urps = self.MOVING_URPS[(sample_position, self.dest)]
            for urp in urps:
                robot_arm.run_program(urp)

            self.lab_manager.move_sample(sample_id=self.sample, position=self.dest)
            self.logger.log_device_signal({
                "device": robot_arm.name,
                "sample_id": self.sample,
                "src": sample_positions[RobotArm][sample_position][0],
                "dest": sample_positions[RobotArm][self.dest][0],
            })
