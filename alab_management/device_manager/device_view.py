import time
from dataclasses import asdict
from datetime import datetime
from enum import Enum, unique, auto
from threading import Lock
from typing import Type, List, Optional, Union, Dict

import pymongo
from bson import ObjectId

from alab_management import BaseDevice
from alab_management.config import config
from alab_management.db import get_collection
from alab_management.device_manager import get_all_devices


@unique
class DeviceStatus(Enum):
    """
    The status of devices
    """
    UNKNOWN = auto()
    IDLE = auto()
    OCCUPIED = auto()


class DevicesLock:
    def __init__(self, devices: Dict[Type[BaseDevice], BaseDevice], device_view: "DeviceView"):
        self.devices: Dict[Type[BaseDevice], BaseDevice] = devices
        self.device_view: "DeviceView" = device_view

    def __enter__(self):
        return self.devices

    def __exit__(self, exc_type, exc_val, exc_tb):
        for device in self.devices.values():
            self.device_view.release_device(device)


class DeviceView:
    """
    Device view provides API to get/set the status of a device
    """

    def __init__(self):
        self._device_collection = get_collection(config["devices"]["device_db"])
        self._device_collection.create_index([("name", pymongo.HASHED)])
        self.device_list = get_all_devices()
        self._lock = Lock()

    def add_devices_to_db(self):
        """
        Insert device definitions to db, which includes devices' name, descriptions, parameters,
        type (class name).

        When one device's name has already appeared in the database, a ``NameError`` will be raised.
        Device name is a unique identifier for a device
        """
        for device in self.device_list.values():
            if self._device_collection.find_one({"name": device.name}) is not None:
                raise NameError(f"Duplicated device name {device.name}, did you cleanup the database?")
            self._device_collection.insert_one({
                "sample_positions": [sample_pos.name for sample_pos in device.sample_positions],
                "status": DeviceStatus.UNKNOWN.name,
                "type": device.__class__.__name__,
                "description": device.description,
                "task_id": None,
                "last_updated": datetime.now(),
                **asdict(device),
            })

    def clean_up_device_db(self):
        """
        Clean up the device database
        """
        self._device_collection.drop()

    def request_devices(self, task_id: ObjectId, *device_type: Type[BaseDevice]):
        """
        Request a list of device, this function will return until all the requested device is ready.

        .. note::
            There should be no duplicated devices in the ``device_type``, or a ``ValueError`` shall be raised

        Args:
            task_id: the id of task that requests these devices
            *device_type: the requested device types

        Returns:

        """
        if len(device_type) != len(set(device_type)):
            raise ValueError("Currently we do not allow duplicated devices in one request.")

        while True:
            idle_devices: Dict[Type[BaseDevice], BaseDevice] = {}
            try:
                self._lock.acquire(blocking=True)
                for device in device_type:
                    result = self.get_device(device_type=device, task_id=task_id, only_idle=True)
                    if not result:
                        break
                    # just pick the first device
                    idle_devices[device] = self.device_list[result[0]]
                else:
                    for device in idle_devices.values():
                        self.occupy_device(device=device, task_id=task_id)
                    return DevicesLock(devices=idle_devices, device_view=self)
            finally:
                self._lock.release()

            time.sleep(1)

    def get_device(self, device_type: Type[BaseDevice], task_id: ObjectId, only_idle: bool = True) -> List[str]:
        """
        Given device type, it will return all the device with this type.

        If only_idle set to True, only the idle devices will be returned (or ones have the same task id)

        Args:
            device_type: the type of device, which should be ``type[BaseDevice]``
            task_id: the id of task that requests this device
            only_idle: only return the idle devices

        Returns:
            A list of devices' name that meet the requirements
        """
        request_dict = {
            "name": device_type.__name__,
        }
        if only_idle:
            request_dict.update({"$or": [{
                "status": DeviceStatus.IDLE.name,
            }, {
                "task_id": task_id,
            }]})
        return [device_entry["name"] for device_entry in self._device_collection.find(request_dict)]

    def occupy_device(self, device: BaseDevice, task_id: ObjectId):
        """
        Occupy a device with given task id
        """
        self._update_status(
            device=device,
            required_status=DeviceStatus.IDLE,
            target_status=DeviceStatus.IDLE,
            task_id=task_id,
        )

    def release_device(self, device: BaseDevice):
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
            raise ValueError(f"Cannot find device ({device_name})")

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
