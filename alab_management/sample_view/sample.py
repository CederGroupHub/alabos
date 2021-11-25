from dataclasses import dataclass, field
from typing import Optional, ClassVar

from bson import ObjectId


@dataclass(frozen=True)
class Sample:
    """
    Basic sample object

    - ``_id``: the unique id of a sample in the database
    - ``name``: the name of this sample
    - ``position``: current position of the sample, if None, which means the sample has not been initialized
      in the lab
    """
    _id: ObjectId
    task_id: Optional[ObjectId]
    name: str
    position: Optional[str]


@dataclass(frozen=True)
class SamplePosition:
    """
    A sample position in the lab

    Sample position is a position in the lab that can hold sample,
    it is not a geographic coordinate in the lab, but a defined
    position in the lab

    - ``name``: the name of this sample position, which is the unique
      identifier of a sample position
    - ``description``: a string that describes the sample position briefly
    """
    SEPARATOR: ClassVar[str] = "/"
    name: str
    number: int = field(default=1)
    description: str = field(default="", compare=False, hash=False)
