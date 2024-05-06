from bson import ObjectId

from alab_management.task_view.task import BaseTask

from ..devices.device_that_never_ends import DeviceThatNeverEnds  # noqa: TID252


class InfiniteTask(BaseTask):
    def __init__(self, samples: list[ObjectId], *args, **kwargs):
        super().__init__(samples=samples, *args, **kwargs)
        self.sample = samples[0]

    def run(self):
        with self.lab_view.request_resources({DeviceThatNeverEnds: {"infinite_loop": 1}}) as (devices, _):
            device_that_never_ends = devices[DeviceThatNeverEnds]
            device_that_never_ends.run_infinite()
