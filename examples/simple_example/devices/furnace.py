from typing import ClassVar

from alab_control.furnace_epc_3016 import FurnaceController

from alab_management import BaseDevice, SamplePosition


class Furnace(BaseDevice):
    description: ClassVar[str] = "Simple furnace"

    def __init__(self, address: str, port: int, *args, **kwargs):
        super(Furnace, self).__init__(*args, **kwargs)
        self.address = address
        self.port = port
        self.driver = FurnaceController(address=address, port=port)

    @property
    def sample_positions(self):
        return [
            SamplePosition(
                "{name}.inside".format(name=self.name),
                description="The position inside the furnace, where the samples are heated"
            ),
            SamplePosition(
                "furnace_table",
                description="Temporary position to transfer samples"
            )
        ]

    def emergent_stop(self):
        self.driver.stop()
