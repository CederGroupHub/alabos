"""This module contains the Starting task class."""

from alab_management import BaseTask


class Starting(BaseTask):
    """This class represents the Starting task."""

    def __init__(self, start_position: str, *args, **kwargs):
        """Initialize the Starting task."""
        super().__init__(*args, **kwargs)

        self.start_position = start_position
        self.sample = self.samples[0]

    def validate(self):
        """Validate the Starting task."""
        if len(self.samples) != 1:
            raise ValueError(
                f"Starting task can only be used with one sample, but {len(self.samples)} were given."
            )
        return True

    def run(self):
        """Run the Starting task."""
        self.set_message(
            f"Requesting user to move sample {self.sample} to starting position {self.start_position}"
        )
        with self.lab_view.request_resources({None: {self.start_position: 1}}) as (
            _,
            sample_positions,
        ):
            position = sample_positions[None][self.start_position][0]
            response = self.lab_view.request_user_input(
                prompt=f"Move {self.sample} to {position}",
                options=["success", "error"],
            )
            if response == "error":
                raise Exception(
                    f"User said they were unable to move {self.sample} to {position}!"
                )

            self.lab_view.move_sample(
                sample=self.sample,
                position=position,
            )
        self.set_message(f"Sample was moved to {position}.")
