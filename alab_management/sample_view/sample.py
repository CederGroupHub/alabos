"""The definition of the Sample and SamplePosition classes."""

import os
from dataclasses import dataclass, field
from typing import Any, ClassVar

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
    task_id: ObjectId | None
    name: str
    position: str | None
    metadata: dict[str, Any] = field(default_factory=dict)
    tags: list[str] = field(default_factory=list)


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


# _standalone_sample_position_registry is used to store all the standalone sample positions that are defined in the __init__.py
# when setting up the lab.
# it is only pooled with new sample positions that are added to the lab during reload.
_standalone_sample_position_registry: dict[str, SamplePosition] = {}

# _current_standalone_sample_position_registry is used to store all the standalone sample positions that are defined in the __init__.py
# when alabos setup is called, regardless of whether it is a reload or not.
# this is used to check if a sample position is still in the lab during reload.
# if not, it will be removed from the lab once unoccupied and devices that are related to it are also not occupied.
# this is not visible to the sample_view
_current_standalone_sample_position_registry: dict[str, SamplePosition] = {}


def add_standalone_sample_position(position: SamplePosition):
    """Register a device instance."""
    if not isinstance(position, SamplePosition):
        raise TypeError(
            f"The type of position should be SamplePosition, but user provided {type(position)}"
        )
    if position.name in _standalone_sample_position_registry and not os.environ.get(
        "ALABOS_RELOAD", None
    ):
        raise KeyError(f"Duplicated standalone sample position name {position.name}")
    _standalone_sample_position_registry[position.name] = position
    _current_standalone_sample_position_registry[position.name] = position


def get_all_standalone_sample_positions() -> dict[str, SamplePosition]:
    """Get all the sample position names in the registry."""
    return _standalone_sample_position_registry.copy()


def get_current_standalone_sample_positions() -> dict[str, SamplePosition]:
    """Get all the current standalone sample positions in the registry."""
    return _current_standalone_sample_position_registry.copy()


def remove_standalone_sample_position(prefix: str):
    """Remove a standalone sample position from the registry."""
    _standalone_sample_position_registry.pop(prefix, None)
    _current_standalone_sample_position_registry.pop(prefix, None)


def reset_current_standalone_sample_position_registry():
    """Reset the current standalone sample position registry."""
    _current_standalone_sample_position_registry.clear()
