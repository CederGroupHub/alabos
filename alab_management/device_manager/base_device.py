from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List, ClassVar, Dict

from alab_management.sample_manager.sample import SamplePosition


@dataclass
class BaseDevice(ABC):
    """
    The abstract class of device

    All the defined classes should be inherited from this class

    Attributes:
        name: the name of device, which is the unique identifier of this device
        description: description of this kind of device, which can include the device type, how to set up and so on.
    """
    name: str
    description: ClassVar[str] = ""

    @abstractmethod
    def init(self):
        """
        ``init`` method can be used to initialized the device with provided parameters.

        .. note::
          You should never try to set up connection with device in ``__init__`` or ``__post_init__``, or the
          program may not be able to initialize successfully!
        """
        raise NotImplementedError()

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


def get_device(name: str):
    """
    Get device by name
    """
    return _device_registry[name]


def get_all_devices() -> Dict[str, BaseDevice]:
    """
    Get all the device names in the device registry
    """
    return _device_registry.copy()
