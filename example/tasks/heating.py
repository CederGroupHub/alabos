from dataclasses import dataclass, field
from typing import List

from alab_control.furnace_epc_3016 import Segment

from alab_management.op_def.base_operation import BaseOperation
from ..devices.furnace import Furnace


@dataclass
class Heating(BaseOperation):
    furnace: Furnace = field(hash=False, compare=False)
    segments: List[Segment] = field(hash=True, compare=True)

    @property
    def operation_location(self):
        return "{}.inside".format(self.furnace.name)

    @property
    def occupied_positions(self):
        return self.furnace.name

    def __call__(self):
        self.furnace.run_program(*self.segments)

    def is_running(self):
        return self.furnace.is_running()
