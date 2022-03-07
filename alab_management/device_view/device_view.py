from datetime import datetime
from enum import unique, Enum, auto
from typing import List, Optional, Union, Dict, Any, Collection, cast, TypeVar

import pymongo
from bson import ObjectId

from .device import BaseDevice, get_all_devices
from ..utils.data_objects import get_collection, get_lock

_DeviceType = TypeVar("_DeviceType", bound=BaseDevice)


@unique
class DeviceStatus(Enum):
    """
    The status of devices
    """
    UNKNOWN = auto()
    IDLE = auto()
    OCCUPIED = auto()
    ERROR = auto()
    HOLD = auto()


class DeviceView:
    """
    Device view provides API to get/set the status
    of a device as well as request ownership of one device
    """

    def __init__(self):
        self._device_collection = get_collection("devices")
        self._device_collection.create_index([("name", pymongo.HASHED)])
        self._device_list = get_all_devices()
        self._lock = get_lock(self._device_collection.name)

    def sync_device_status(self):
        """
        Sync the device status (usually when the system is set up)

        Some devices may still be running, so it is not usable now. We will set the
        status to ``OCCUPIED``
        """
        for device in self._device_list.values():
            status = DeviceStatus.OCCUPIED if device.is_running() else DeviceStatus.IDLE
            self._update_status(device=device.name,
                                target_status=status,
                                required_status=None,
                                task_id=None)

    def add_devices_to_db(self):
        """
        Insert device definitions to db, which includes devices' name, descriptions, parameters,
        type (class name).

        When one device's name has already appeared in the database, a ``NameError`` will be raised.
        Device name is a unique identifier for a device
        """
        for device in self._device_list.values():
            if self._device_collection.find_one({"name": device.name}) is not None:
                raise NameError(f"Duplicated device name {device.name}, did you cleanup the database?")
            self._device_collection.insert_one({
                "name": device.name,
                "description": device.description,
                "type": device.__class__.__name__,
                "sample_positions": [sample_pos.name for sample_pos in device.sample_positions],
                "status": DeviceStatus.IDLE.name,
                "task_id": None,
                "created_at": datetime.now(),
                "last_updated": datetime.now(),
            })

    def get_all(self) -> List[Dict[str, Any]]:
        """
        Get all the devices in the database, used for dashboard
        """
        return cast(List[Dict[str, Any]], self._device_collection.find())

    def clean_up_device_collection(self):
        """
        Clean up the device collection
        """
        self._device_collection.drop()

    def request_devices(
            self,
            task_id: ObjectId,
            device_types_str: Collection[str],  # pylint: disable=unsubscriptable-object
    ) -> Optional[Dict[str, Dict[str, Union[str, bool]]]]:
        """
        Request a list of device, this function will return the name of devices if all the requested device is ready.

        .. note::
            There should be no duplicated devices in the ``device_type``, or a ``ValueError`` shall be raised

        Args:
            task_id: the id of task that requests these devices
            device_types_str: the requested device types

        Returns:
            {"device_type_name": {"name": device_name, "need_release": need_release (bool)}} or None
        """
        if len(device_types_str) != len(set(device_types_str)):
            raise ValueError("Currently we do not allow duplicated devices in one request.")

        idle_devices: Dict[str, Dict[str, Union[str, bool]]] = {}
        with self._lock():  # pylint: disable=not-callable
            for device in device_types_str:
                result = self.get_available_devices(device_type_str=device, task_id=task_id)
                if not result:  # Cannot meet all the requirements, return None
                    return None
                # just pick the first device
                idle_devices[device] = next(filter(lambda device_: not device_["need_release"], result), result[0])
            return idle_devices

    def get_available_devices(self, device_type_str: str, task_id: Optional[ObjectId]) \
            -> List[Dict[str, Union[str, bool]]]:
        """
        Given device type, it will return all the device with this type.

        If only_idle set to True, only the idle devices will be returned (or ones have the same task id)

        Args:
            device_type_str: the type of device
            task_id: the id of task that requests this device

        Returns:
            [{"name": device_name, "need_release": bool}]
            The entry need_release indicates whether a device needs to be released
            when __exit__ method is called in the ``DevicesLock``.
        """
        request_dict = {
            "type": device_type_str,
        }
        if self._device_collection.find_one(request_dict) is None:
            raise ValueError(f"No such device_type: {device_type_str}")

        request_dict.update({"$or": [{  # type: ignore
            "status": DeviceStatus.IDLE.name,
        }, {
            "task_id": task_id,
        }]})

        return [{
            "name": device_entry["name"],
            "need_release": not device_entry["task_id"] == task_id,
        } for device_entry in self._device_collection.find(request_dict)]

    def get_device(self, device_name: str) -> Optional[Dict[str, Any]]:
        """
        Get device by device name, if not found, return ``None``
        """
        return self._device_collection.find_one({"name": device_name})

    def get_status(self, device_name: str) -> DeviceStatus:
        """
        Get device status by device name, if not found, raise ``ValueError``
        """
        device_entry = self.get_device(device_name=device_name)

        if device_entry is None:
            raise ValueError(f"Cannot find device with name: {device_name}")
        return DeviceStatus[device_entry["status"]]

    def occupy_device(self, device: Union[BaseDevice, str], task_id: ObjectId):
        """
        Occupy a device with given task id
        """
        self._update_status(
            device=device,
            required_status=DeviceStatus.IDLE,
            target_status=DeviceStatus.OCCUPIED,
            task_id=task_id,
        )

    def get_devices_by_task(self, task_id: Optional[ObjectId]) -> List[BaseDevice]:
        """
        Get devices given a task id (regardless of its status!)
        """
        return [self._device_list[device["name"]]
                for device in self._device_collection.find({"task_id": task_id})]

    def release_device(self, device: Union[BaseDevice, str]):
        """
        Release a device
        """
        self._update_status(
            device=device,
            required_status=None,
            target_status=DeviceStatus.IDLE,
            task_id=None
        )

    def _update_status(self, device: Union[BaseDevice, str],
                       required_status: Optional[Union[DeviceStatus, List[DeviceStatus]]],
                       target_status: DeviceStatus, task_id: Optional[ObjectId]):
        """
        A method that check and update the status of a device

        If ``task_id`` is the same as the task id in queried sample,
        we will just skip the status check specified by ``required_status``
        """
        if isinstance(device, BaseDevice):
            device_name = device.name
        else:
            device_name = device

        device_entry = self._device_collection.find_one({"name": device_name})

        if device_entry is None:
            raise ValueError(f"Cannot find device ({device_name}). Did you run `setup` command?")

        required_status = [required_status] \
            if isinstance(required_status, DeviceStatus) \
            else required_status

        # if task_id has the same value, we will not check the current status
        if device_entry["task_id"] == task_id:
            required_status = None

        if required_status is not None and \
                DeviceStatus[device_entry["status"]] not in required_status:
            raise ValueError(f"Device's status ({device_entry['status']}) is "
                             f"not in {[status.name for status in required_status]}")

        self._device_collection.update_one({"name": device_name}, {"$set": {
            "status": target_status.name,
            "task_id": task_id,
            "last_updated": datetime.now(),
        }})

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
            raise AttributeError(f"Cannot find method with name: {prop} on {device_name}")

        return getattr(device, prop)

    def execute_command(self, device_name: str, method: str, *args, **kwargs):
        """
        Call a callable function (``method``) with ``*args`` and ``**kwargs`` on ``device_name``
        """
        return self.query_property(device_name=device_name, prop=method)(*args, **kwargs)
