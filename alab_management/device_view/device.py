"""Define the base class of devices."""

import datetime
import functools
import os
import threading
import time
from abc import ABC, abstractmethod
from collections.abc import Callable
from queue import Empty, PriorityQueue
from traceback import format_exc
from typing import Any
from unittest.mock import Mock

from alab_management.logger import DBLogger
from alab_management.sample_view.sample import SamplePosition
from alab_management.user_input import request_maintenance_input

from .dbattributes import DictInDatabase, ListInDatabase


def _UNSPECIFIED(_):
    return None


def mock(
    return_constant: Any = _UNSPECIFIED,
    object_type: list[Any] | Any = _UNSPECIFIED,
):
    """
    A decorator used for mocking functions during simulation.

    Args:
        return_constant (Any, optional): The constant value to be returned by the mocked function.
            It can be a value (str, int, float, bool), list of values, or a dictionary specifying
            return values for keys. Default is None.
        object_type (Union[List[Any], Any], optional): The type or list of types to mock if the
            function returns an object. Default is None.

    Returns
    -------
        Decorator function used to mock other functions during simulation.

    Raises
    ------
        ValueError: If both `return_constant` and `object_type` are specified.
        ValueError: If `return_constant` is not of types: str, int, float, bool, list, or dict.
        ValueError: If `object_type` is specified and not a list or a class type.

    .. note ::

        The decorator mocks the function during simulation based on specified constant values or object types.

    Examples
    --------
    1. Mocking a function with a constant return value:

    .. code-block:: python

        @mock(return_constant=42)
        def get_data() -> int:
            ...
            a = some_integer
            return a

    2. Mocking a function that returns multiple values in a dictionary:

    .. code-block:: python

        @mock(return_constant={"twotheta": [0.1, 0.2, 0.3], "counts": [100, 200, 300]})
        def run_simulation() -> dict:
            ...
            a = {twotheta: [0.1, 0.2, 0.3]}
            b = {counts: [100, 200, 300]}
            return {**a, **b}

    3. Mocking a function that returns a specific object type:

    .. code-block:: python

        @mock(object_type=str)
        def create_mock_string() -> str:
            return "Mocked String"

    4. Mocking a function that returns a single object type:

    .. code-block:: python

        from alab_control.ohaus_scale import OhausScale as ScaleDriver

        @mock(object_type=ScaleDriver)
        def get_driver(self):
            self.driver = ScaleDriver(ip=self.ip_address, timeout=self.TIMEOUT)
            self.driver.set_unit_to_mg()
            return self.driver

    5. Mocking a function that returns a list of object types:

    .. code-block:: python

        from alab_control.furnace_2416 import FurnaceController
        from alab_control.door_controller import DoorController

        @mock(object_type=[FurnaceController, DoorController])
        def get_driver(self):
            self.driver = FurnaceController(port=self.com_port)
            return self.driver, self.door_controller
    """

    def decorator(f: Callable[..., Any]):
        @functools.wraps(f)
        def wrapper(*args, **kwargs):
            from alab_management.config import AlabOSConfig

            if AlabOSConfig().is_sim_mode():
                if (
                    return_constant is not _UNSPECIFIED
                    and object_type is not _UNSPECIFIED
                ):
                    raise ValueError(
                        "Cannot specify both return_constant and return_mock_call!"
                    )
                elif isinstance(return_constant, dict):
                    return_dict = {key: return_constant[key] for key in return_constant}
                    return return_dict
                elif isinstance(return_constant, list):
                    return list(range(len(return_constant)))
                elif return_constant is not _UNSPECIFIED:
                    return return_constant
                elif object_type is not _UNSPECIFIED:
                    if isinstance(object_type, list):
                        return [Mock(spec=cls) for cls in object_type]
                    else:
                        return Mock(spec=object_type)
                else:
                    raise ValueError(
                        "Must specify either return_constant or object_type! return_constant should "
                        "be of the type str, int, float, bool, list or dict. "
                        "object_type should be any other class that you want to mock."
                    )
            else:
                return f(*args, **kwargs)

        return wrapper

    return decorator


# Base Device class #
class BaseDevice(ABC):
    """
    The abstract class of device.

    All the devices should be inherited from this class

    Attributes
    ----------
        name (str): the name of device, which is the unique identifier of this device
        description (Optional[str]): description of this kind of device, which can include
              the device type, how to set up and so on.
        args: arguments that will be passed to the device class
        kwargs: keyword arguments that will be passed to the device class
    """

    def __init__(self, name: str, description: str | None = None, *args, **kwargs):
        """
        Initialize a device object, you can set up connection to
        the device in this method. The device will only be initialized
        once in the system. So if your connection to driver need to be
        renewed from time to time, you can write a custom function to
        connect to the device when needed.

        Args:
            name: the name of device, which is the unique identifier of this device
            description: description of this kind of device

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
            self.description = description  # TODO: change this

        self.name = name

        if not isinstance(self.description, str):
            raise TypeError("description must be a string")

        from alab_management.device_view import DeviceView

        self._device_view = DeviceView()
        self._signalemitter = DeviceSignalEmitter(
            device=self
        )  # this will periodically log any device methods that are decorated with @log_signal!

    @property
    @abstractmethod
    def description(self) -> str:
        """
        A short description of the device. This will be stored in the database + displayed in the dashboard. This
        must be declared in subclasses of BaseDevice!.
        """
        return self._description

    @description.setter
    def description(self, value: str) -> None:
        if not isinstance(value, str):
            raise TypeError("description must be a string")
        self._description = value

    def set_message(self, message: str):
        """Sets the device message to be displayed on the dashboard.

        Note: this method is used instead of python getter/setters because the DeviceWrapper can currently only
        access methods, not properties.
        """
        self._device_view.set_message(device_name=self.name, message=message)
        self.__message = message

    def get_message(self) -> str:
        """Returns the device message to be displayed on the dashboard.

        Note: this method is used instead of python getter/setters because the DeviceWrapper can currently only
        access methods, not properties.
        """
        self.__message = self._device_view.get_message(device_name=self.name)
        return self.__message

    def _connect_wrapper(self):
        """
        Connect to the device and execute any backend actions that are only possible when alabos is running + the
        device is connected.

        Note that device's only connect within `alabos launch`, so ExperimentManager, DeviceManager, and the API are
        guaranteed to be running when this method is called.
        """
        self.connect()
        self.get_message()  # retrieve the most recent message from the database.
        self._signalemitter.start()  # start the signal emitter thread

    @abstractmethod
    def connect(self):
        """
        Connect to any devices here. This will be called by alabos to make connections to devices at the appropriate
        time.

        This method must be defined even if no device connections are required! Just return in this case.

        """
        raise NotImplementedError()

    def _disconnect_wrapper(self):
        """Disconnect from the device and execute any backend actions that are only possible when alabos is running."""
        self.disconnect()
        self._signalemitter.stop()

    @abstractmethod
    def disconnect(self):
        """
        Disconnect from devices here. This will be called by alabos to release connections to devices at the
        appropriate time.

        This method must be defined even if no device connections are required! Just return in this case.
        """
        raise NotImplementedError()

    @property
    @abstractmethod
    def sample_positions(self) -> list[SamplePosition]:
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
                      number=8,
                  ),
                  SamplePosition(
                      "furnace_table",
                      description="Temporary position to transfer samples",
                      number=16,
                  ),
              ]

        """
        raise NotImplementedError()

    @abstractmethod
    def is_running(self) -> bool:
        """Check whether this device is running."""
        raise NotImplementedError()

    # methods to store Device values inside the database. Lists and dictionaries are supported.
    def list_in_database(
        self, name: str, default_value: list | None | None = None
    ) -> ListInDatabase:
        """
        Create a list attribute that is stored in the database.
        Note: nested dicts/lists are not supported!.

        Args:
            name: The name of the attribute
            default_value: The default value of the attribute. if None (default), will default to an empty list.

        Returns
        -------
            Class instance to access the attribute. Acts like a normal List, but is stored in the database.
        """
        return ListInDatabase(
            device_collection=self._device_view._device_collection,
            device_name=self.name,
            attribute_name=name,
            default_value=default_value,
        )

    def dict_in_database(
        self, name: str, default_value: dict | None | None = None
    ) -> DictInDatabase:
        """
        Create a dict attribute that is stored in the database.
        Note: nested dicts/lists are not supported!.

        Args:
            name: The name of the attribute
            default_value: The default value of the attribute. if None (default), will default to an empty dict.

        Returns
        -------
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

        This is called when the device is first added to the database, typically only when alabos is setting up a new
        lab.
        """
        for attribute_name in dir(self):
            attribute = getattr(self, attribute_name)
            if any(isinstance(attribute, t) for t in [ListInDatabase, DictInDatabase]):
                attribute.apply_default_value()

    def request_maintenance(self, prompt: str, options: list[Any]):
        """
        Request maintenance input from the user. This will display a prompt to the user and wait for them to select
        an option. The selected option will be returned.

        Args:
            prompt: the text to display to the user
            options: the options to display to the user. This should be a list of strings.
        """
        return request_maintenance_input(prompt=prompt, options=options)

    def retrieve_signal(
        self, signal_name: str, within: datetime.timedelta | None = None
    ):
        """
        Retrieve a signal from the database.

        Args:
            signal_name (str): device signal name. This should match the signal_name passed to the
              ``@log_device_signal`` decorator
            within (Optional[datetime.timedelta], optional):
              timedelta defining how far back to pull logs from (relative to current time). Defaults to None.

        Returns
        -------
            Dict: Dictionary of signal result. Single value vs lists depends on whether ``within`` was None
            or not, respectively. Form is: { "device_name": "device_name", "signal_name": "signal_name",
            "value": "signal_value" or ["signal_value_1", "signal_value_2", ...]], "timestamp": "timestamp" or [
            "timestamp_1", "timestamp_2", ...] }
        """
        return self._signalemitter.retrieve_signal(signal_name, within)


# DeviceSignalEmitter and related decorator #
def log_signal(signal_name: str, interval_seconds: int):
    """This is a decorator for methods within a `BaseDevice`. Methods decorated with this will be called at the
    specified interval and the result will be logged to the database under the `signal_name` provided. The intended
    use is to track process variables (like a furnace temperature, a pressure sensor, etc.) whenever the device is
    connected to alabos.

    Args:
        signal_name (str): Name to attribute to this signal
        interval_seconds (int): Interval at which to log this signal to the database.
    """

    def wrapper(func):
        def wrapper_func(self, *args, **kwargs):
            value = func(self, *args, **kwargs)
            return value

        wrapper_func.logging_interval_seconds = interval_seconds
        wrapper_func.signal_name = signal_name

        return wrapper_func

    return wrapper


class DeviceSignalEmitter:
    """
    This class is responsible for periodically logging device signals to the database.
    It is intended to be used as a singleton, and should be instantiated once per device.
    """

    def __init__(self, device: BaseDevice):
        from alab_management.device_view import DeviceView

        self._device_view: DeviceView = DeviceView()
        self.dblogger = DBLogger(task_id=None)
        self.device = device
        self.is_logging = False
        self.queue: PriorityQueue = PriorityQueue()

        self._logging_thread: threading.Thread | None = None
        self._start_time: datetime.datetime | None = None

    def get_methods_to_log(self):
        """
        Log the data from all methods decorated with ``@log_signal`` to the database.

        Collected all the methods that are decorated with ``@log_signal`` and return a dictionary of the form:

        .. code-block::

            {
                <method_name>: {
                    "interval": <interval_seconds>,
                    "signal_name": <signal_name>
                }
            }
        """
        methods_to_log = {}
        for method_name, method in self.device.__class__.__dict__.items():
            if hasattr(method, "logging_interval_seconds") and callable(method):
                methods_to_log[method_name] = {
                    "interval": method.logging_interval_seconds,
                    "signal_name": method.signal_name,
                }
        return methods_to_log

    def _worker(self):
        """This is the worker thread that will periodically log device signals to the database."""

        def wait_with_option_to_kill(time_to_wait: float):
            """
            Waits until the next log is due, or until the logging is stopped. When stopping
            the logging worker, the worker will complete its current logging task before
            stopping the worker thread. This may result in long blockages if the logging
            interval is long. This function will allow the worker to periodically check if
            it should stop mid-wait to avoid this issue.

            Args:
                time_to_wait (float): The total time to wait, assuming the logging worker is not stopped.
            """
            if time_to_wait < 0:
                # we are behind schedule, don't wait at all!
                return

            total_time_to_wait = time_to_wait
            while total_time_to_wait > 0:
                if not self.is_logging:
                    return
                time_to_wait = min(
                    total_time_to_wait, 0.2
                )  # we will wait 0.2 second at a time
                total_time_to_wait -= time_to_wait
                time.sleep(time_to_wait)

        if len(self.get_methods_to_log()) == 0:
            return  # no need to run if we aren't logging any methods

        while True:
            # we check if logging is active within the loop. This is to allow the logging worker
            # to be stopped mid-wait if necessary. Prevents us blocking a `.stop()` call if stuck
            # waiting to log method on a long interval.
            try:
                log_at, method_name, signal_name, interval, count = self.queue.get(
                    block=False
                )
            except Empty:
                # wait for queue to refill. We shouldn't reach this under normal circumstances
                time.sleep(1)
                continue
            time_until_this_log = (log_at - datetime.datetime.now()).total_seconds()
            wait_with_option_to_kill(time_until_this_log)
            if not self.is_logging:
                break
            self.log_method_to_db(method_name=method_name, signal_name=signal_name)

            count += 1
            next_log_at = self._start_time + datetime.timedelta(
                seconds=interval * count
            )
            self.queue.put((next_log_at, method_name, signal_name, interval, count))

    def log_method_to_db(self, method_name: str, signal_name: str):
        """
        Logs a method to the database. This is called by the worker thread.

        Args:
            method_name: the name of the method to call on the device
            signal_name: the name of the signal to log to the database

        Exceptions:
            Any exceptions raised by the method call will be caught and raised directly.
        """
        method = getattr(self.device, method_name)
        try:
            value = method()
        except Exception:
            value = (
                f"Error reading {method_name} from device {self.device.name}."
                f"The error message is: "
                f"{format_exc()}"
            )

        self.dblogger.log_device_signal(
            device_name=self.device.name,
            signal_name=signal_name,
            signal_value=value,
        )

    def start(self):
        """
        Start the logging worker thread. This will start logging all
        methods decorated with `@log_signal` to the database.
        """
        self.queue = PriorityQueue()
        for method_name, logging_properties in self.get_methods_to_log().items():
            # queue items are tuples of the form:
            # tuple(
            #      0. timestamp of next log,
            #      1. method name (to get value from device),
            #      2. signal name (what to call this in the database),
            #      3. interval (seconds),
            #      4. count (how many times this has been logged since starting)
            #  )
            self.queue.put(
                (
                    datetime.datetime.now()
                    + datetime.timedelta(seconds=logging_properties["interval"]),
                    method_name,
                    logging_properties["signal_name"],
                    logging_properties["interval"],
                    1,
                )
            )
        self.is_logging = True
        self._logging_thread = threading.Thread(target=self._worker)
        self._start_time = datetime.datetime.now()

        self._logging_thread.start()

    def stop(self):
        """Stop the logging worker thread. This will stop logging all."""
        self.is_logging = False
        self._logging_thread.join()

    def retrieve_signal(self, signal_name, within: datetime.timedelta | None = None):
        """Retrieve a signal from the database.

        Args:
            signal_name (str): device signal name. This should match the signal_name
              passed to the `@log_device_signal` decorator
            within (Optional[datetime.timedelta]): timedelta defining
              how far back to pull logs from (relative to current time). Defaults to None.

        Returns
        -------
            Dict: Dictionary of signal result. Single value vs lists depends on whether ``within``
              was None or not, respectively. Form is:

            .. code-block::
            {
                "device_name": "device_name",
                "signal_name": "signal_name",
                "value": "signal_value" or ["signal_value_1", "signal_value_2", ...]],
                "timestamp": "timestamp" or ["timestamp_1", "timestamp_2", ...]
            }
        """
        if within is None:
            return self.dblogger.get_latest_device_signal(
                device_name=self.device.name, signal_name=signal_name
            )
        else:
            return self.dblogger.filter_device_signal(
                device_name=self.device.name, signal_name=signal_name, within=within
            )


_device_registry: dict[str, BaseDevice] = {}


def add_device(device: BaseDevice):
    """Register a device instance. It is stored in a global dictionary."""
    if device.name in _device_registry and not os.environ.get("ALABOS_RELOAD", None):
        raise KeyError(f"Duplicated device name {device.name}")
    _device_registry[device.name] = device


def get_all_devices() -> dict[str, BaseDevice]:
    """
    Get all the device names in the device registry. This is a shallow copy of the registry.

    Returns
    -------
        A dictionary of all the devices in the registry. The keys are the device names,
          and the values are the device instances.
    """
    return _device_registry.copy()
