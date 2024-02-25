"""The definition of the Sample and SamplePosition classes."""

from dataclasses import dataclass, field
from typing import Any, ClassVar, Dict, List, Optional

from bson import ObjectId  # type: ignore


@dataclass(frozen=True)
class Sample:
    """
    Basic sample object.

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
    metadata: Dict[str, Any] = field(default_factory=dict)
    tags: List[str] = field(default_factory=list)


@dataclass(frozen=True)
class SamplePosition:
    """
    A sample position in the lab.

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
        """Check if the number of sample position is valid."""
        if self.number < 0:
            raise ValueError(
                f"{self.number} is an invalid number of sample positions! The number of sample position ({self.name}) "
                f"must be >= 0."
            )


_standalone_sample_position_registry: Dict[str, SamplePosition] = {}


def add_standalone_sample_position(position: SamplePosition):
    """Register a device instance."""
    if not isinstance(position, SamplePosition):
        raise TypeError(
            f"The type of position should be SamplePosition, but user provided {type(position)}"
        )
    if position.name in _standalone_sample_position_registry:
        raise KeyError(f"Duplicated standalone sample position name {position.name}")
    _standalone_sample_position_registry[position.name] = position


def get_all_standalone_sample_positions() -> Dict[str, SamplePosition]:
    """Get all the device names in the device registry."""
    return _standalone_sample_position_registry.copy()
