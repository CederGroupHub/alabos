"""Wrapper over the ``devices`` collection."""

import time
from collections.abc import Collection
from datetime import datetime
from enum import Enum, auto, unique
from typing import Any, TypeVar, cast

import pymongo  # type: ignore
from bson import ObjectId  # type: ignore

from alab_management.sample_view import SamplePosition, SampleView
from alab_management.utils.data_objects import get_collection, get_lock

from .device import BaseDevice, get_all_devices

_DeviceType = TypeVar("_DeviceType", bound=BaseDevice)  # pylint: disable=invalid-name


class DeviceConnectionError(Exception):
    """Generic error signifying that connection to a device has failed."""


@unique
class DeviceTaskStatus(Enum):
    """The Task status of devices. Used by TaskManager to decide whether a Device is available for to execute a Task."""

    UNKNOWN = auto()
    IDLE = auto()
    OCCUPIED = auto()
    ERROR = auto()


@unique
class DevicePauseStatus(Enum):
    """Pause status of the Device. This is used to pause the device outside of the typical Task queue (like by an
    operator for maintenance or refilling consumables).
    """

    RELEASED = auto()
    REQUESTED = auto()
    PAUSED = auto()


class DeviceView:
    """
    Device view provides API to get/set the status
    of a device as well as request ownership of one device.
    """

    def __init__(self, connect_to_devices: bool = False):
        """Class with methods to interact with devices (status + method execution).

        Args:
            connect_to_devices (Optional[bool]): If true, make a connection to all devices
              (serial, ip, etc.). If False, can still check Device status, but cannot execute
              methods on devices. Defaults to False.
        """
        self._device_collection = get_collection("devices")
        self._device_collection.create_index([("name", pymongo.HASHED)])
        self._device_list = get_all_devices()
        self._lock = get_lock(self._device_collection.name)
        self._sample_view = SampleView()
        self.__connected_to_devices = False

        if connect_to_devices:
            self.__connect_all_devices()

    def __connect_all_devices(self):
        for device_name, device in self._device_list.items():
            try:
                device._connect_wrapper()
            except Exception as e:
                raise DeviceConnectionError(
                    f"Could not connect to {device_name}!"
                ) from e
            print(f"Connected to {device_name}")
        self.__connected_to_devices = True

    def __disconnect_all_devices(self):
        for device_name, device in self._device_list.items():
            try:
                device._disconnect_wrapper()
            except Exception as e:
                raise DeviceConnectionError(
                    f"Could not disconnect from {device_name}!"
                ) from e
            print(f"Disconnected from {device_name}")
        self.__connected_to_devices = False

    def sync_device_status(self):
        """
        Sync the device status (usually when the system is set up).

        Some devices may still be running, so it is not usable now. We will set the
        status to ``OCCUPIED``
        """
        for device in self._device_list.values():
            status = (
                DeviceTaskStatus.OCCUPIED
                if device.is_running()
                else DeviceTaskStatus.IDLE
            )
            self._update_status(
                device=device.name,
                target_status=status,
                required_status=None,
                task_id=None,
            )

    def add_devices_to_db(self):
        """
        Insert device definitions to db, which includes devices' name, descriptions, parameters,
        type (class name).

        When one device's name has already appeared in the database, a ``NameError`` will be raised.
        Device name is a unique identifier for a device
        """
        for device in self._device_list.values():
            if self._device_collection.find_one({"name": device.name}) is not None:
                raise NameError(
                    f"Duplicated device name {device.name}, did you cleanup the database?"
                )
            self._device_collection.insert_one(
                {
                    "name": device.name,
                    "description": device.description,
                    "type": device.__class__.__name__,
                    "sample_positions": [
                        f"{device.name}{SamplePosition.SEPARATOR}{sample_pos.name}"
                        for sample_pos in device.sample_positions
                    ],
                    "status": DeviceTaskStatus.IDLE.name,
                    "pause_status": DevicePauseStatus.RELEASED.name,
                    "task_id": None,
                    "created_at": datetime.now(),
                    "message": "",
                    "last_updated": datetime.now(),
                    "attributes": {},
                }
            )

    def get_all(self) -> list[dict[str, Any]]:
        """Get all the devices in the database, used for dashboard."""
        return cast(list[dict[str, Any]], self._device_collection.find())

    def _clean_up_device_collection(self):
        """Clean up the device collection."""
        self._device_collection.drop()

    def request_devices(
        self,
        task_id: ObjectId,
        device_names_str: Collection[str] | None = None,
        device_types_str: (
            Collection[str] | None
        ) = None,  # pylint: disable=unsubscriptable-object
    ) -> dict[str, dict[str, str | bool]] | None:
        """
        Request a list of device, this function will return the name of devices if all the requested device is ready.

        .. note::
            There should be no duplicated devices in the ``device_type``, or a ``ValueError`` shall be raised

        Args:
            task_id (ObjectId): the id of task that requests these devices
            device_names_str (Optional[Collection[str]]): the requested
              device names. If None, no device name is requested
            device_types_str (Optional[Collection[str]]): the requested
              device types. If None, no device type is requested

        Returns
        -------
            {"device_type_name": {"name": device_name, "need_release": need_release (bool)}} or None
        """
        if device_names_str is None:
            device_names_str = []

        if device_types_str is None:
            device_types_str = []

        if len(device_types_str) != len(set(device_types_str)):
            raise ValueError(
                "Currently we do not allow duplicated device types in one request."
            )

        idle_devices: dict[str, dict[str, str | bool]] = {}
        with self._lock():  # pylint: disable=not-callable
            for device_name in device_names_str:
                result = self.get_available_devices(
                    device_str=device_name, type_or_name="name", task_id=task_id
                )
                if not result:
                    return None  # cannot meet all requirement, return None
                idle_devices[device_name] = result[0]
            for device in device_types_str:
                result = self.get_available_devices(
                    device_str=device, type_or_name="type", task_id=task_id
                )
                if not result:
                    return None
                same_task_devices = list(
                    filter(lambda device_: not device_["need_release"], result)
                )
                if len(same_task_devices) > 0:
                    # just pick the first device
                    idle_devices[device] = same_task_devices[0]
                else:
                    # if no device is held by the same task, pick the device with least samples
                    minimum_number_of_samples = 999999999
                    for device_ in result:
                        samples_on_device_ = self.get_samples_on_device(device_["name"])
                        number_of_samples_in_device_ = sum(
                            len(samples) for samples in samples_on_device_.values()
                        )
                        if number_of_samples_in_device_ < minimum_number_of_samples:
                            minimum_number_of_samples = number_of_samples_in_device_
                            idle_devices[device] = device_
            return idle_devices

    def get_available_devices(
        self, device_str: str, type_or_name: str, task_id: ObjectId | None = None
    ) -> list[dict[str, str | bool]]:
        """
        Given device type, it will return all the device with this type.

        If only_idle set to True, only the idle devices will be returned (or ones have the same task id)

        Args:
            device_str (str): the type of device
            type_or_name: "type" or "name" to specify whether searching for a type of device by
              Type(BaseDevice), or for a specific device by name
            task_id: the id of task that requests this device

        Returns
        -------
            [{"name": device_name, "need_release": bool}]
            The entry need_release indicates whether a device needs to be released
            when __exit__ method is called in the ``DevicesLock``.
        """
        if type_or_name == "type":
            request_dict = {
                "type": device_str,
            }
        elif type_or_name == "name":
            request_dict = {"name": device_str}
        else:
            raise ValueError(f"Unknown type_or_name: {type_or_name}")

        if self._device_collection.find_one(request_dict) is None:
            raise ValueError(f"No such device of {type_or_name} {device_str}")

        request_dict.update(
            {
                "$or": [
                    {  # type: ignore
                        "$and": [
                            {"status": DeviceTaskStatus.IDLE.name},
                            {"pause_status": DevicePauseStatus.RELEASED.name},
                        ]
                    },
                    {
                        "task_id": task_id,
                    },
                ]
            }
        )

        return [
            {
                "name": device_entry["name"],
                # if device already held by this task, don't release with
                # this request. Will be released by the older request.
                "need_release": device_entry["task_id"] != task_id,
            }
            for device_entry in self._device_collection.find(request_dict)
        ]

    def get_device(self, device_name: str) -> dict[str, Any]:
        """Get device by device name, if not found, raises ``ValueError``."""
        device_entry = self._device_collection.find_one({"name": device_name})
        if device_entry is None:
            raise ValueError(f"Cannot find device with name: {device_name}")
        return device_entry

    def get_status(self, device_name: str) -> DeviceTaskStatus:
        """Get device status by device name, if not found, raise ``ValueError``."""
        device_entry = self.get_device(device_name=device_name)
        return DeviceTaskStatus[device_entry["status"]]

    def occupy_device(self, device: BaseDevice | str, task_id: ObjectId):
        """Occupy a device with given task id."""
        self._update_status(
            device=device,
            required_status=DeviceTaskStatus.IDLE,
            target_status=DeviceTaskStatus.OCCUPIED,
            task_id=task_id,
        )
        device_name = device.name if isinstance(device, BaseDevice) else device
        # Wait until the device status has been updated to OCCUPIED
        while (
            self.get_status(device_name=device_name).name
            != DeviceTaskStatus.OCCUPIED.name
        ):
            time.sleep(0.5)

    def get_devices_by_task(self, task_id: ObjectId | None) -> list[BaseDevice]:
        """Get devices given a task id (regardless of its status!)."""
        return [
            self._device_list[device["name"]]
            for device in self._device_collection.find({"task_id": task_id})
        ]

    def release_device(self, device_name: str):
        """
        Release a device.

        device: name of device to be released
        """
        device_entry = self.get_device(device_name=device_name)

        update_dict = {
            "task_id": None,
            "last_updated": datetime.now(),
            "status": DeviceTaskStatus.IDLE.name,
        }

        if (
            DevicePauseStatus[device_entry["pause_status"]]
            == DevicePauseStatus.REQUESTED
        ):
            update_dict.update(
                {
                    "pause_status": DevicePauseStatus.PAUSED.name,
                }
            )

        self._device_collection.update_one(
            {"name": device_name},
            {"$set": update_dict},
        )
        # wait until the device status has been updated to IDLE
        while self.get_status(device_name=device_name).name != "IDLE":
            time.sleep(0.5)

    def get_samples_on_device(self, device_name: str):
        """Get all samples on a device."""
        device = self.get_device(device_name=device_name)
        _sample_collection = get_collection("samples")

        samples_per_position = {}
        for position in device["sample_positions"]:
            samples = _sample_collection.find({"position": {"$regex": position}})
            samples_per_position[position] = [sample["_id"] for sample in samples]
        return samples_per_position

    def _update_status(
        self,
        device: BaseDevice | str,
        required_status: DeviceTaskStatus | list[DeviceTaskStatus] | None,
        target_status: DeviceTaskStatus,
        task_id: ObjectId | None,
    ):
        """
        A method that check and update the status of a device.

        If ``task_id`` is the same as the task id in queried sample,
        we will just skip the status check specified by ``required_status``
        """
        device_name = device.name if isinstance(device, BaseDevice) else device

        device_entry = self._device_collection.find_one({"name": device_name})

        if device_entry is None:
            raise ValueError(
                f"Cannot find device ({device_name}). Did you run `setup` command?"
            )

        required_status = (
            [required_status]
            if isinstance(required_status, DeviceTaskStatus)
            else required_status
        )

        # if task_id has the same value, we will not check the current status
        if device_entry["task_id"] == task_id:
            required_status = None

        if (
            required_status is not None
            and DeviceTaskStatus[device_entry["status"]] not in required_status
        ):
            raise ValueError(
                f"Device's current status ({device_entry['status']}) is "
                f"not in allowed set of statuses {[status.name for status in required_status]}. "
                f"Cannot change status to {target_status.name}"
            )
        self._device_collection.update_one(
            {"name": device_name},
            {
                "$set": {
                    "status": target_status.name,
                    "task_id": task_id,
                    "last_updated": datetime.now(),
                }
            },
        )

    def query_property(self, device_name: str, prop: str):
        """
        Query the property value of a device (with ``device_name``) with ``prop``.

        If there is no such device with name ``device_name``, a ``ValueError`` shall be raised.
        If there is no such property with name ``prop``, a ``AttributeError`` shall be raised.
        """
        if device_name not in self._device_list:
            raise ValueError(f"Cannot find device with name: {device_name}")
        device: BaseDevice = self._device_list[device_name]

        if not hasattr(device, prop):
            raise AttributeError(
                f"Cannot find method with name: {prop} on {device_name}"
            )

        return getattr(device, prop)

    def execute_command(self, device_name: str, method: str, *args, **kwargs):
        """Call a callable function (``method``) with ``*args`` and ``**kwargs`` on ``device_name``."""
        if not self.__connected_to_devices:
            raise Exception(
                "DeviceView cannot execute device commands without first connecting to the devices!"
            )
        device_method = self.query_property(device_name=device_name, prop=method)
        return device_method(*args, **kwargs)

    def set_message(self, device_name: str, message: str):
        """Sets the device message. Message is used to communicate device state with the user dashboard.

        Args:
            device_name (str): name of the device to set the message for
            message (str): message to be set
        """
        self.get_device(device_name=device_name)
        self._device_collection.update_one(
            {"name": device_name},
            {"$set": {"message": message, "last_updated": datetime.now()}},
        )

    def get_message(self, device_name: str) -> str:
        """Gets the current device message. Message is used to communicate device state with the user dashboard.

        Args:
            device_name (str): name of the device to set the message for
        """
        return self.get_device(device_name=device_name)["message"]

    def get_all_attributes(self, device_name: str) -> dict[str, Any]:
        """Returns the device attributes.

        Args:
            device_name (str): name of the device to get the attributes for

        Returns
        -------
            dict: device attributes
        """
        device = self.get_device(device_name=device_name)
        return device["attributes"]

    def get_attribute(self, device_name: str, attribute: str) -> Any:
        """Gets a device attribute. Attributes are used to store device-specific values in the database.

        Args:
            device_name (str): name of the device to get the attribute for
            attribute (str): attribute to be retrieved

        Returns
        -------
            Any: attribute value
        """
        device = self.get_device(device_name=device_name)
        if attribute not in device["attributes"]:
            raise AttributeError(
                f"Device {device_name} does not have attribute {attribute}"
            )
        return device["attributes"][attribute]

    def set_all_attributes(self, device_name: str, attributes: dict):
        """Sets the device attributes.

        Args:
            device_name (str): name of the device to set the attributes for
            attributes (dict): attributes to be set
        """
        self.get_device(device_name=device_name)
        self._device_collection.update_one(
            {"name": device_name},
            {
                "$set": {
                    "attributes": attributes,
                    "last_updated": datetime.now(),
                }
            },
        )

    def set_attribute(self, device_name: str, attribute: str, value: Any):
        """Sets a device attribute. Attributes are used to store device-specific values in the database.

        Args:
            device_name (str): name of the device to set the attribute for
            attribute (str): attribute to be set
            value (Any): attribute value
        """
        attributes = self.get_all_attributes(device_name=device_name)
        attributes[attribute] = value
        self._device_collection.update_one(
            {"name": device_name},
            {
                "$set": {
                    "attributes": attributes,
                    "last_updated": datetime.now(),
                }
            },
        )

    def pause_device(self, device_name: str):
        """Request pause for a specific device."""
        # with self._lock():
        device = self.get_device(device_name=device_name)
        new_pause_status = (
            DevicePauseStatus.PAUSED.name
            if device["status"] == DeviceTaskStatus.IDLE.name
            else DevicePauseStatus.REQUESTED.name
        )

        self._device_collection.update_one(
            {"name": device_name},
            {
                "$set": {
                    "pause_status": new_pause_status,
                    "last_updated": datetime.now(),
                }
            },
        )

    def unpause_device(self, device_name: str):
        """Unpause a device."""
        # with self._lock():
        device = self.get_device(device_name=device_name)
        update_dict = {
            "pause_status": DevicePauseStatus.RELEASED.name,
            "last_updated": datetime.now(),
        }

        # Unless the device is currently paused, we will leave its task status unchanged.
        if DevicePauseStatus[device["pause_status"]] == DevicePauseStatus.PAUSED:
            update_dict.update(
                {
                    "status": DeviceTaskStatus.IDLE.name,
                }
            )

        self._device_collection.update_one(
            {"name": device_name},
            {"$set": update_dict},
        )

    def __exit__(self, exc_type, exc_value, traceback):
        """Disconnect from all devices when exiting the context manager."""
        if self.__connected_to_devices:
            self.__disconnect_all_devices()
