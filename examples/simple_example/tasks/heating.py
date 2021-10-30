from dataclasses import dataclass, field
from typing import List, Tuple

from alab_management.op_def.base_operation import BaseOperation
from ..devices.furnace import Furnace


@dataclass
class Heating(BaseOperation):
    furnace: Furnace = field(hash=False, compare=False)
    set_points: List[Tuple[float, float]] = field(hash=True, compare=True)

    @property
    def operation_location(self):
        return "{}.inside".format(self.furnace.name)

    @property
    def occupied_positions(self):
        return [self.furnace.name]

    def run(self, logger):
        ...

    def is_running(self):
        return self.furnace.driver.is_running()
