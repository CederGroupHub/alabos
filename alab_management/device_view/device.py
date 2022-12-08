"""
Define the base class of devices
"""

from abc import ABC, abstractmethod
from typing import Any, List, ClassVar, Dict, Optional, Union

from alab_management.sample_view.sample import SamplePosition
from .dbattributes import value_in_database, ListInDatabase, DictInDatabase


class BaseDevice(ABC):
    """
    The abstract class of device

    All the devices should be inherited from this class

    Attributes:
        description: description of this kind of device, which can include
              the device type, how to set up and so on.
    """

    def __init__(self, name: str, description: Optional[str] = None, *args, **kwargs):
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
        # override default class description if provided during device instantiation.
        if description:
            self.description = description
        self.name = name

        if not isinstance(self.description, str):
            raise TypeError("description must be a string")

        from alab_management.device_view import DeviceView

        self._device_view = DeviceView()

    @property
    @abstractmethod
    def description(self) -> str:
        """
        A short description of the device. This will be stored in the database + displayed in the dashboard. This must be declared in subclasses of BaseDevice!
        """
        pass

    def set_message(self, message: str):
        """Sets the device message to be displayed on the dashboard.

        Note: this method is used instead of python getter/setters because the DeviceWrapper can currently only access methods, not properties.
        """
        self._device_view.set_message(device_name=self.name, message=message)
        self.__message = message

    def get_message(self) -> str:
        """Returns the device message to be displayed on the dashboard.

        Note: this method is used instead of python getter/setters because the DeviceWrapper can currently only access methods, not properties.
        """
        self.__message = self._device_view.get_message(device_name=self.name)
        return self.__message

    def _connect_wrapper(self):
        """
        Connect to the device and execute any backend actions that are only possible when alabos is running + the device is connected.

        Note that device's only connect within `alabos launch`, so ExperimentManager, DeviceManager, and the API are guaranteed to be running when this method is called.
        """
        self.connect()
        self.get_message()  # retrieve the most recent message from the database.

    @abstractmethod
    def connect(self):
        """
        Connect to any devices here. This will be called by alabos to make connections to devices at the appropriate time.

        This method must be defined even if no device connections are required! Just return in this case.

        """
        raise NotImplementedError()

    def _disconnect_wrapper(self):
        """
        Disconnect from the device and execute any backend actions that are only possible when alabos is running.
        """
        self.disconnect()

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
                      "inside",
                      description="The position inside the furnace, where the samples are heated",
                      number=8
                  ),
                  SamplePosition(
                      "furnace_table",
                      description="Temporary position to transfer samples",
                      number=16
                  )
              ]

        """
        raise NotImplementedError()

    @abstractmethod
    def emergent_stop(self):  # TODO rename this to emergency stop
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

    ## methods to store Device values inside the database. Lists and dictionaries are supported.
    def list_in_database(
        self, name: str, default_value: Optional[Union[list, None]] = None
    ) -> ListInDatabase:
        """
        Create a list attribute that is stored in the database.
        Note: nested dicts/lists are not supported!

        Args:
            name: The name of the attribute
            default_value: The default value of the attribute. if None (default), will default to an empty list.

        Returns:
            Class instance to access the attribute. Acts like a normal List, but is stored in the database.
        """
        return ListInDatabase(
            device_collection=self._device_view._device_collection,
            device_name=self.name,
            attribute_name=name,
            default_value=default_value,
        )

    def dict_in_database(
        self, name: str, default_value: Optional[Union[dict, None]] = None
    ) -> DictInDatabase:
        """
        Create a dict attribute that is stored in the database.
        Note: nested dicts/lists are not supported!

        Args:
            name: The name of the attribute
            default_value: The default value of the attribute. if None (default), will default to an empty dict.

        Returns:
            Class instance to access the attribute. Acts like a normal Dict, but is stored in the database.
        """
        return DictInDatabase(
            device_collection=self._device_view._device_collection,
            device_name=self.name,
            attribute_name=name,
            default_value=default_value,
        )

    def _apply_default_db_values(self):
        """
        Apply default values to attributes that are stored in the database.

        This is called when the device is first added to the database, typically only when alabos is setting up a new lab.
        """
        for attribute_name in dir(self):
            attribute = getattr(self, attribute_name)
            if any(isinstance(attribute, t) for t in [ListInDatabase, DictInDatabase]):
                attribute.apply_default_value()


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
