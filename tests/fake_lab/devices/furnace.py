from threading import Timer
from typing import ClassVar

from alab_management.device_view import BaseDevice
from alab_management.sample_view import SamplePosition


class Furnace(BaseDevice):
    """Fake furnace device."""

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
                number=8,  # eight samples can be heated at the same time
            ),
        ]

    def emergent_stop(self):
        pass

    def run_program(self, *segments):
        self._is_running = True

        # segments is expected to be a list of (temp, duration) tuples
        # If segments is a tuple of tuples, flatten it
        if len(segments) == 1 and isinstance(segments[0], list | tuple):
            segments = segments[0]
        total_duration = sum(float(seg[1]) for seg in segments)

        def finish():
            self._is_running = False

        t = Timer(total_duration, finish)
        t.start()

    def is_running(self):
        return self._is_running

    def get_temperature(self):
        return 300

    def connect(self):
        pass

    def disconnect(self):
        pass
