from dataclasses import dataclass, field

from bson import ObjectId


@dataclass
class Sample:
    _id: ObjectId
    position: str


@dataclass
class SamplePosition:
    name: str
    description: str = field(compare=False, hash=False)
