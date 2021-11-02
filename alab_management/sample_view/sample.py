from dataclasses import dataclass, field
from typing import Optional

from bson import ObjectId


@dataclass(frozen=True)
class Sample:
    """
    Basic sample object

    Attributes:
        _id: the unique id of a sample in the database
        position: current position of the sample, if None,
            which means the sample has not been initialized
            in the lab
    """
    _id: ObjectId
    position: Optional[str]


@dataclass(frozen=True)
class SamplePosition:
    """
    A sample position in the lab

    Sample position is a position in the lab that can hold sample,
    it is not a geographic coordinate in the lab, but a defined
    position in the lab

    Attributes:
        name: the name of this sample position, which is the unique
            identifier of a sample position
        description: a string that describes the sample position briefly
    """
    name: str
    description: str = field(compare=False, hash=False)
