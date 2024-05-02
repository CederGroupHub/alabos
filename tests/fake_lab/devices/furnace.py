from threading import Timer
from typing import ClassVar

from alab_management.device_view import BaseDevice
from alab_management.sample_view import SamplePosition


class Furnace(BaseDevice):
    description: ClassVar[str] = "Fake furnace"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._is_running = False

    @property
    def sample_positions(self):
        return [
            SamplePosition(
                "inside",
                description="The position inside the furnace, where the samples are heated",
                number=8,
            ),
        ]

    def emergent_stop(self):
        pass

    def run_program(self, *segments):
        self._is_running = True

        def finish():
            self._is_running = False

        t = Timer(0.1, finish)
        t.start()

    def is_running(self):
        return self._is_running

    def get_temperature(self):
        return 300

    def connect(self):
        pass

    def disconnect(self):
        pass
