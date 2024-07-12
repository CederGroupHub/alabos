from typing import cast

from bson import ObjectId

from alab_management.task_view.task import BaseTask

from ..devices.robot_arm import RobotArm  # noqa


class Moving(BaseTask):
    def __init__(self, samples: list[str | ObjectId], dest: str, *args, **kwargs):
        super().__init__(samples=samples, *args, **kwargs)
        self.sample = samples[0]
        self.dest = dest
        self.sample_position = self.lab_view.get_sample(sample=self.sample).position

    def run(self):
        with self.lab_view.request_resources(
            {RobotArm: {}, None: {self.dest: 1, self.sample_position: 1}}
        ) as (devices, sample_positions):
            robot_arm = cast(RobotArm, devices[RobotArm])
            robot_arm.run_program(
                f"{sample_positions[None][self.sample_position][0]}-{self.dest}.urp"
            )
            self.lab_view.move_sample(self.sample, self.dest)
            self.logger.log_device_signal(
                device_name=robot_arm.name,
                signal_name="MoveSample",
                signal_value={
                    "src": sample_positions[None][self.sample_position][0],
                    "dest": sample_positions[None][self.dest][0],
                },
            )
        return self.task_id
