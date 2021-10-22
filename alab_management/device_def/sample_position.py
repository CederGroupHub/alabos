from dataclasses import dataclass, field


@dataclass
class SamplePosition:
    name: str
    description: str = field(compare=False, hash=False)
    num: int = field(compare=False, hash=False)

    def __post_init__(self):
        if self.num < 0:
            raise ValueError("The num of sample position should be >= 0.")
