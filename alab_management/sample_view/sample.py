"""
The definition of the Sample and SamplePosition classes.
"""

from dataclasses import dataclass, field
from typing import Optional, ClassVar, Dict, Type

from bson import ObjectId


@dataclass(frozen=True)
class Sample:
    """
    Basic sample object

    - ``sample_id``: the unique id of a sample in the database
    - ``task_id``: the unique id of a task that currently "owns" (is processing) this sample
    - ``name``: the name of this sample
    - ``position``: current position of the sample in the lab. if None, the sample has not been initialized
      in the lab
    """

    sample_id: ObjectId
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

    def __post_init__(self):
        if self.number < 0:
            raise ValueError(
                f"{self.number} is an invalid number of sample positions! The number of sample position ({self.name}) must be >= 0."
            )


_standalone_sample_position_registry: Dict[str, SamplePosition] = {}


def add_standalone_sample_position(position: SamplePosition):
    """
    Register a device instance
    """
    if not isinstance(position, SamplePosition):
        raise TypeError(
            f"The type of position should be SamplePosition, but user provided {type(position)}"
        )
    if position.name in _standalone_sample_position_registry:
        raise KeyError(f"Duplicated standalone sample position name {position.name}")
    _standalone_sample_position_registry[position.name] = position


def get_all_standalone_sample_positions() -> Dict[str, SamplePosition]:
    """
    Get all the device names in the device registry
    """
    return _standalone_sample_position_registry.copy()
