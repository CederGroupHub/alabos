import random
from threading import Timer
from typing import ClassVar

from alab_management import BaseDevice, SamplePosition


class Furnace(BaseDevice):
    description: ClassVar[str] = "Fake furnace"

    def __init__(self, *args, **kwargs):
        super(Furnace, self).__init__(*args, **kwargs)
        self._is_running = False

    @property
    def sample_positions(self):
        return [
            SamplePosition(
                "{name}/inside".format(name=self.name),
                description="The position inside the furnace, where the samples are heated",
            ),
            SamplePosition(
                "furnace_table", description="Temporary position to transfer samples"
            ),
            SamplePosition(
                "furnace_temp",
                number=4,
                description="Test positions",
            ),
        ]

    def emergent_stop(self):
        pass

    def run_program(self, *segments):
        self._is_running = True

        def finish():
            self._is_running = False

        t = Timer(2, finish)
        t.start()

    def is_running(self):
        return self._is_running

    def get_temperature(self):
        return 300

    def connect(self):
        pass

    def disconnect(self):
        pass


furnace_1 = Furnace(name="furnace_1")
furnace_2 = Furnace(name="furnace_2")
furnace_3 = Furnace(name="furnace_3")
furnace_4 = Furnace(name="furnace_4")
