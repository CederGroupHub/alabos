"""
Define the base class of devices
"""

from abc import ABC, abstractmethod
from typing import List, ClassVar, Dict

from ..sample_view.sample import SamplePosition


class BaseDevice(ABC):
    """
    The abstract class of device

    All the devices should be inherited from this class
    """

    description: ClassVar[str] = ""

    def __init__(self, name: str):
        """
        Initialize a device object, you can set up connection to
        the device in this method. The device will only be initialized
        once in the system. So if your connection to driver need to be
        renewed from time to time, you can write a custom function to
        connect to the device when needed.

        Args:
            name: the name of device, which is the unique identifier of this device
            description: description of this kind of device, which can include
              the device type, how to set up and so on.

        Here is an example of how to write a new device

        .. code-block:: python

          def __init__(self, address: str, port: int = 502, *args, **kwargs):
              super(Furnace, self).__init__(*args, **kwargs)
              self.address = address
              self.port = port
              self.driver = FurnaceController(address=address, port=port)
        """
        self.name = name

    @property
    @abstractmethod
    def sample_positions(self) -> List[SamplePosition]:
        """
        The sample positions describe the position that can hold a sample. The name of sample
        position will be the unique identifier of this sample position. It does not store any
        coordinates information about where the position is in the lab. Users need to map the
        sample positions to real lab coordinates manually.

        .. note::
          It doesn't matter in which device class a sample position is defined.
          We use ``name`` attribute to identify them.

        Here is an example of how to define some sample positions

        .. code-block:: python

          @property
          def sample_positions(self):
              return [
                  SamplePosition(
                      f"{self.name}.inside",
                      description="The position inside the furnace, where the samples are heated"
                  ),
                  SamplePosition(
                      "furnace_table",
                      description="Temporary position to transfer samples"
                  )
              ]

        """
        raise NotImplementedError()

    @abstractmethod
    def emergent_stop(self):
        """
        Specify how the device should stop when emergency
        """
        raise NotImplementedError()

    @abstractmethod
    def is_running(self) -> bool:
        """
        Check whether this device is running
        """
        raise NotImplementedError()


_device_registry: Dict[str, BaseDevice] = {}


def add_device(device: BaseDevice):
    """
    Register a device instance
    """
    if device.name in _device_registry:
        raise KeyError(f"Duplicated device name {device.name}")
    _device_registry[device.name] = device


def get_all_devices() -> Dict[str, BaseDevice]:
    """
    Get all the device names in the device registry
    """
    return _device_registry.copy()
