from dataclasses import dataclass, field
from typing import List, Any, Dict

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
    task_args: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if self.containers is None:
            self.containers = config["general"]["containers"]

        for container in self.containers:
            if container not in config["general"]["containers"]:
                raise ValueError(f"Undefined container: {container}, please define it in config file.")
