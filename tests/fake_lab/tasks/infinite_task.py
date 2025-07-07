from bson import ObjectId

from alab_management.task_view.task import BaseTask

from ..devices.device_that_never_ends import DeviceThatNeverEnds  # noqa: TID252


class InfiniteTask(BaseTask):
    def __init__(self, samples: list[str | ObjectId], *args, **kwargs):
        """Infinite task.

        Args:
            samples (list[str|ObjectId]): List of sample names or sample IDs.
        """
        super().__init__(samples=samples, *args, **kwargs)
        self.sample = samples[0]

    def run(self):
        with self.lab_view.request_resources({DeviceThatNeverEnds: {}}) as (inner_devices, _):
            while True:
                pass
