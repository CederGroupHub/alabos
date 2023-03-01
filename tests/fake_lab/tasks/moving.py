from typing import cast, List

from bson import ObjectId

from alab_management.task_view.task import BaseTask
from ..devices.robot_arm import RobotArm


class Moving(BaseTask):
    def __init__(self, samples: List[ObjectId], dest: str, *args, **kwargs):
        super(Moving, self).__init__(samples=samples, *args, **kwargs)
        self.sample = samples[0]
        self.dest = dest
        self.sample_position = self.lab_view.get_sample(sample_id=self.sample).position

    def run(self):
        with self.lab_view.request_resources({RobotArm: {self.sample_position: 1, self.dest: 1}}) \
                as (devices, sample_positions):
            robot_arm = cast(RobotArm, devices[RobotArm])
            robot_arm.run_program(f"{sample_positions[RobotArm][self.sample_position][0]}-{self.dest}.urp")
            self.lab_view.move_sample(self.sample, self.dest)
            self.logger.log_device_signal({
                "device": robot_arm.name,
                "sample_id": self.sample,
                "src": sample_positions[RobotArm][self.sample_position][0],
                "dest": sample_positions[RobotArm][self.dest][0],
            })
        return self.task_id
