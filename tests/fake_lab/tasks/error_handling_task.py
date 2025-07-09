from bson import ObjectId

from alab_management.task_view.task import BaseTask
from tests.fake_lab.devices import DeviceThatFails  # noqa: TID252


class ErrorHandlingUnrecoverable(BaseTask):
    """Error handling unrecoverable task."""

    def __init__(self, samples: list[str | ObjectId], *args, **kwargs):
        """Error handling unrecoverable task.

        Args:
            samples (list[str|ObjectId]): List of sample names or sample IDs.
        """
        super().__init__(samples=samples, *args, **kwargs)
        self.sample = samples[0]

    def run(self):
        with self.lab_view.request_resources({DeviceThatFails: {"failures": 1}}) as (
            inner_devices,
            _,
        ):
            device_that_fails = inner_devices[DeviceThatFails]
            device_that_fails.fail()


class ErrorHandlingRecoverable(BaseTask):
    """Error handling recoverable task."""

    def __init__(self, samples: list[str | ObjectId], *args, **kwargs):
        """Error handling recoverable task.

        Args:
            samples (list[str|ObjectId]): List of sample names or sample IDs.
        """
        super().__init__(samples=samples, *args, **kwargs)
        self.sample = samples[0]

    def run(self):
        with self.lab_view.request_resources({DeviceThatFails: {"failures": 1}}) as (
            devices,
            _,
        ):
            device_that_fails_ = devices[DeviceThatFails]
            try:
                device_that_fails_.fail()
            except Exception as e:
                response = self.lab_view.request_user_input(
                    "What should I do?", options=["OK", "Abort"]
                )
                if response == "OK":
                    pass
                else:
                    raise e
