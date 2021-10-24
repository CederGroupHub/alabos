from dataclasses import dataclass
from typing import ClassVar

from alab_control.furnace_epc_3016 import FurnaceController

from alab_management.device_def import BaseDevice, SamplePosition


@dataclass
class Furnace(BaseDevice):
    name: str
    address: str
    port: int = 502

    description: ClassVar[str] = "Simple furnace"

    def __post_init__(self):
        self.driver = None

    def init(self):
        self.driver = FurnaceController(address=self.address)

    @property
    def sample_positions(self):
        return [
            SamplePosition(
                "{name}.inside".format(name=self.name),
                num=4,
                description="The position inside the furnace, where the samples are heated"
            ),
            SamplePosition(
                "furnace_table",
                num=1,
                description="Temporary position to transfer samples"
            )
        ]
