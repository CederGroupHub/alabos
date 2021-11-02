"""
Define the base class of devices
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List, ClassVar, Dict


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
    name: str
    description: str = field(compare=False, hash=False)


@dataclass
class BaseDevice(ABC):
    """
    The abstract class of device

    All the defined classes should be inherited from this class

    - ``name``: the name of device, which is the unique identifier of this device
    - ``description``: description of this kind of device, which can include
      the device type, how to set up and so on.
    """
    name: str
    description: ClassVar[str] = ""

    @property
    @abstractmethod
    def sample_positions(self) -> List[SamplePosition]:
        """
        The sample positions describe the position that can hold a sample.

        .. note::
          It doesn't matter in which device class a sample position is defined.
          We use ``name`` attribute to identify them.
        """
        raise NotImplementedError()


_device_registry: Dict[str, BaseDevice] = {}


def add_device(device: BaseDevice):
    """
    Register a device instance
    """
    if device.name in _device_registry:
        raise KeyError("Duplicated device name {}".format(device.name))
    _device_registry[device.name] = device


def get_all_devices() -> Dict[str, BaseDevice]:
    """
    Get all the device names in the device registry
    """
    return _device_registry.copy()
