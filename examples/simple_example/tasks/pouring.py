from bson import ObjectId

from alab_management.task_view.task import BaseTask
from ..devices.robot_arm import RobotArm


class Pouring(BaseTask):
    def __init__(self, sample: ObjectId, *args, **kwargs):
        super(Pouring, self).__init__(*args, **kwargs)
        self.sample = sample

    def run(self):
        with self.lab_view.request_resources({RobotArm: []}) as (devices, sample_positions):
            robot_arm: RobotArm = devices[RobotArm]
            robot_arm.run_program("vial_pour_2.urp")
            self.logger.log_device_signal({
                "device": RobotArm.__name__,
                "msg": "Pour powder into crucible."
            })
