from dataclasses import dataclass

from bson import ObjectId

from alab_management.task_view.task import BaseTask
from ..devices.robot_arm import RobotArm


@dataclass
class Moving(BaseTask):
    def __init__(self, sample: ObjectId, dest: str, *args, **kwargs):
        super(Moving, self).__init__(*args, **kwargs)
        self.sample = sample
        self.dest = dest

    def run(self):
        sample = self.lab_manager.get_sample(sample_id=self.sample)
        sample_position = sample.position

        with self.lab_manager.request_resources({RobotArm: [sample_position, self.dest]}) \
                as devices_and_positions:
            devices, sample_positions = devices_and_positions
            robot_arm: RobotArm = devices[RobotArm]
            robot_arm.run_program(f"{sample_positions[sample_position]}-{self.dest}.urp")
            self.lab_manager.move_sample(self.sample, p[1])
            self.logger.log_device_signal({
                "device": robot_arm.name,
                "sample_id": self.sample,
                "src": sample_positions[sample_position],
                "dest": sample_positions[self.dest],
            })
