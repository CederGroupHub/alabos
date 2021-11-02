from dataclasses import dataclass, field
from typing import List, Tuple

from alab_management import BaseOperation


@dataclass
class Heating(BaseOperation):
    set_points: List[Tuple[float, float]] = field(hash=True, compare=True)

    def run(self):
        ...
