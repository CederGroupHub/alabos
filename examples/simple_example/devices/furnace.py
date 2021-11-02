from dataclasses import dataclass, field
from typing import ClassVar

from alab_control.furnace_epc_3016 import FurnaceController

from alab_management import BaseDevice, SamplePosition


@dataclass
class Furnace(BaseDevice):
    name: str
    address: str
    port: int = 502
    driver: FurnaceController = field(default=None, init=False)

    description: ClassVar[str] = "Simple furnace"

    def init(self):
        self.driver = FurnaceController(address=self.address)

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
