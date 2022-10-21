"""
Define the base class of devices
"""

from abc import ABC, abstractmethod
from typing import Any, List, ClassVar, Dict

from alab_management.sample_view.sample import SamplePosition


def attribute_in_database(name: str, default_value: Any) -> property:
    """Property factory to mirror a Device attribute in the ALab database

    Args:
        name (str): attribute name
        default_value (Any): default value for the attribute. Note that this value is not used until the first time a property is queried; at this time, if the attribute is not found in the database, it is set to this value.

    Returns:
        property: class property that handles getting/setting values from the database.


    Example usage when defining a new Device:

        .. code-block:: python
        from alab_management.device_view import BaseDevice, attribute_in_database

        class MyDevice(BaseDevice):
            my_attribute = attribute_in_database("my_attribute", 0)

            def __init__(self, name: str, **kwargs):
                super().__init__(name, **kwargs)
                self.name = name
                self.my_attribute #initial call to the property, which sets the default value in the database

        ....
        #first instantiation

        mydevice = MyDevice(name = "mydevice_1")
        mydevice.my_attribute = 5 #sets the value in the database

        ....
        #future instantiation
        mydevice = MyDevice(name = "mydevice_1")
        mydevice.my_attribute #retrieves value from db and returns 5


    """

    def getter(self) -> Any:
        attributes = self._device_view.get_all_attributes(device_name=self.name)
        if name not in attributes:
            attributes[name] = default_value
            self._device_view.set_all_attributes(self.name, attributes=attributes)
        return attributes[name]

    def setter(self, value: Any) -> None:
        self._device_view.set_attribute(
            device_name=self.name, attribute=name, value=value
        )

    return property(getter, setter)


class BaseDevice(ABC):
    """
    The abstract class of device

    All the devices should be inherited from this class

    Attributes:
        description: description of this kind of device, which can include
              the device type, how to set up and so on.
    """

    description: ClassVar[str] = ""

    def __init__(self, name: str, *args, **kwargs):
        """
        Initialize a device object, you can set up connection to
        the device in this method. The device will only be initialized
        once in the system. So if your connection to driver need to be
        renewed from time to time, you can write a custom function to
        connect to the device when needed.

        Args:
            name: the name of device, which is the unique identifier of this device

        Here is an example of how to write a new device

        .. code-block:: python

          def __init__(self, address: str, port: int = 502, *args, **kwargs):
              super(Furnace, self).__init__(*args, **kwargs)
              self.address = address
              self.port = port
              self.driver = FurnaceController(address=address, port=port)
        """
        from alab_management.device_view import DeviceView

        self.name = name
        self._device_view = DeviceView()
        if "description" in kwargs:
            self.description = kwargs["description"]

    @property
    def message(self):
        return self._message

    @message.setter
    def message(self, message: str):
        self.set_message(message)

    def set_message(self, message: str):
        """Sets the device message to be displayed on the dashboard.

        We need this method in addition to `@message.setter` because the DeviceWrapper can currently only access methods, not properties.
        """
        self._message = message
        self._device_view.set_message(device_name=self.name, message=message)

    @abstractmethod
    def connect(self):
        """
        Connect to any devices here. This will be called by alabos to make connections to devices at the appropriate time.

        This method must be defined even if no device connections are required! Just return in this case.

        """
        raise NotImplementedError()

    @abstractmethod
    def disconnect(self):
        """
        Disconnect from devices here. This will be called by alabos to release connections to devices at the appropriate time.

        This method must be defined even if no device connections are required! Just return in this case.
        """
        raise NotImplementedError()

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
