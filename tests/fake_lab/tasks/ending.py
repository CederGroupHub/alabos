from bson import ObjectId

from alab_management.task_view.task import BaseTask


class Ending(BaseTask):
    """Ending task."""

    def __init__(self, samples: list[str | ObjectId], *args, **kwargs):
        """Ending task.

        Args:
            samples (list[str|ObjectId]): List of sample names or sample IDs.
        """
        super().__init__(samples=samples, *args, **kwargs)
        self.sample = samples[0]

    def run(self):
        """Run the ending task."""
        self.lab_view.move_sample(self.sample, None)
        return self.task_id
