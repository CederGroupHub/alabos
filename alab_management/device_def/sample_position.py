from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class SamplePosition:
    name: str
    description: str = field(compare=False, hash=False)
    num: int = field(compare=False, hash=False)
    container: Optional[List[str]] = field(default_factory=list)
    alias: List[str] = field(default_factory=list, compare=False, hash=False)

    def __post_init__(self):
        if self.num < 0:
            raise ValueError("The num of sample position should be >= 0.")

        if isinstance(self.container, str):
            self.container = list(self.container)
