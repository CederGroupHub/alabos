from dataclasses import dataclass, field
from typing import List

from alab_management.config import config


@dataclass
class SamplePosition:
    name: str
    description: str = field(compare=False, hash=False)


@dataclass
class SamplePositionPair:
    src: str
    dest: str
    containers: List[str] = field(default=None)

    def __post_init__(self):
        if self.containers is None:
            self.containers = config["sample_positions"]["containers"]

        for container in self.containers:
            if container not in config["sample_positions"]["containers"]:
                raise ValueError(f"Undefined container: {container}, please define it in config file.")
