from dataclasses import dataclass, field
from typing import List, Tuple

from alab_management import BaseTask


@dataclass
class Heating(BaseTask):
    set_points: List[Tuple[float, float]] = field(hash=True, compare=True)

    def run(self):
        ...
