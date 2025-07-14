from bson import ObjectId

from alab_management.task_view.task import BaseTask


class Moving(BaseTask):
    """Moving task."""

    def __init__(self, samples: list[str | ObjectId], dest: str, *args, **kwargs):
        """Moving task.

        Args:
            samples (list[str|ObjectId]): List of sample names or sample IDs.
            dest (str): The destination position name.
        """
        super().__init__(samples=samples, *args, **kwargs)
        self.sample = samples[0]
        self.dest = dest
        self.sample_position = self.lab_view.get_sample(sample=self.sample).position

    def run(self):
        """Run the moving task."""
        # Import RobotArm locally to avoid circular import
        from .. import RobotArm

        with self.lab_view.request_resources(
            {RobotArm: {}, None: {self.dest: 1, self.sample_position: 1}}
        ) as (inner_devices, sample_positions):
            sample_destination = sample_positions[None][self.dest][0]
            robot_arm: RobotArm = inner_devices[RobotArm]
            robot_arm.run_program(
                f"{sample_positions[None][self.sample_position][0]}-{self.dest}.urp"
            )
            self.lab_view.move_sample(self.sample, sample_destination)
            self.logger.log_device_signal(
                device_name=robot_arm.name,
                signal_name="MoveSample",
                signal_value={
                    "src": sample_positions[None][self.sample_position][0],
                    "dest": sample_destination,
                },
            )
        return self.task_id
