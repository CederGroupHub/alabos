from bson import ObjectId

from alab_management.task_view.task import BaseTask

from ..devices.device_that_fails import DeviceThatFails  # noqa: TID252


class ErrorHandlingUnrecoverable(BaseTask):
    def __init__(self, samples: list[ObjectId], *args, **kwargs):
        super().__init__(samples=samples, *args, **kwargs)
        self.sample = samples[0]

    def run(self):
        with self.lab_view.request_resources({DeviceThatFails: {"failures": 1}}) as (devices, _):
            device_that_fails = devices[DeviceThatFails]
            device_that_fails.fail()


class ErrorHandlingRecoverable(BaseTask):
    def __init__(self, samples: list[ObjectId], *args, **kwargs):
        super().__init__(samples=samples, *args, **kwargs)
        self.sample = samples[0]

    def run(self):
        with self.lab_view.request_resources({DeviceThatFails: {"failures": 1}}) as (devices, _):
            device_that_fails_ = devices[DeviceThatFails]
            try:
                device_that_fails_.fail()
            except Exception as e:
                response = self.lab_view.request_user_input("What should I do?", options=["OK", "Abort"])
                if response == "OK":
                    pass
                else:
                    raise e
