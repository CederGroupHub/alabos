from dataclasses import dataclass

from bson import ObjectId

from alab_management.task_view.task import BaseTask
from ..devices.robot_arm import RobotArm


@dataclass
class Moving(BaseTask):
    LONG_TIME_TASK = False

    def __init__(self, sample: ObjectId, dest: str, *args, **kwargs):
        super(Moving, self).__init__(*args, **kwargs)
        self.sample = sample
        self.dest = dest

    @staticmethod
    def get_path(src, dest, container):
        # ignore container
        return [(src, dest)]

    def run(self):
        sample = self.lab_manager.get_sample(sample_id=self.sample)
        sample_position = sample.position
        sample_container = sample.container
        path = self.get_path(sample_position, dest=self.dest, container=sample_container)
        all_nodes = [p[0] for p in path] + [self.dest]
        with self.lab_manager.request_resources({RobotArm: [all_nodes]}) as devices_and_positions:
            devices, sample_positions = devices_and_positions
            robot_arm: RobotArm = devices[RobotArm]
            for p in path:
                robot_arm.run_program(f"{p[0]}-{p[1]}-{sample_container}.urp")
                self.logger.log_device_signal({
                    "device": robot_arm.name,
                    "sample_id": sample,
                    "src": p[0],
                    "dest": p[1],
                    "container": sample_container,
                })