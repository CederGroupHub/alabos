from bson import ObjectId
from ..devices.device_that_fails import DeviceThatFails

from alab_management.task_view.task import BaseTask


class ErrorHandling(BaseTask):
    def __init__(self, samples: list[ObjectId], *args, **kwargs):
        super().__init__(samples=samples, *args, **kwargs)
        self.sample = samples[0]

    def run(self):
        with self.lab_view.request_resources({DeviceThatFails: {"failures": 1}}) as (device_that_fails, _):
            device_that_fails.fail()
