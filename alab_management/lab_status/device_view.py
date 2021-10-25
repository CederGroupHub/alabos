from enum import Enum, unique, auto
from typing import Union, Dict, Any, Optional

from bson import ObjectId

from alab_management.config import config
from alab_management.db import get_collection


@unique
class DeviceStatus(Enum):
    """
    The status of devices
    """
    UNKNOWN = auto()
    IDLE = auto()
    RUNNING = auto()
    ERROR = auto()
    HOLD = auto()
    STOPPED = auto()


class DeviceView:
    """
    Device view provide API to get/set the status
    of a device (as well as other basic information
    stored in database)
    """
    _EMPTY_ID = lambda: None  # use lambda as a placeholder for missing id

    def __init__(self):
        self._collection = get_collection(config["devices"]["device_db"])

    def get_status(self, device_name: str) -> DeviceStatus:
        """
        Get the status of device providing ``device_name``

        Args:
            device_name: the name of device, which can be queried by {device.name},
                device should be inherited from
                :py:class:`BaseDevice <alab_management.device_def.base_device.BaseDevice>`.

        Returns:
            The enum class :py:class:`DeviceStatus <DeviceStatus>`
        """
        return DeviceStatus[self.get_device_info(device_name=device_name)["status"]]

    def set_status(self, device_name: str,
                   status: Union[DeviceStatus, str],
                   *,
                   sample_id: Optional[ObjectId] = _EMPTY_ID,
                   task_id: Optional[ObjectId] = _EMPTY_ID):
        """
        Set ``status`` as well as ``task_id`` and ``sample_id`` given a ``device_name``

        Args:
            device_name: the name of device
            status: the status we want to set, which can be :py:class:`DeviceStatus <DeviceStatus>` or ``str``
            sample_id: (optional) current sample's id in the machine. If set to ``None``, the
                last sample_id will be cleared
            task_id: (optional) current task's id running in the machine. If set to ``None``,
                last task_id will be cleared.
        """
        if isinstance(status, DeviceStatus):
            status = status.name
        updated_dict = {
            "status": status,
        }

        if sample_id is not self._EMPTY_ID:
            updated_dict["sample_id"] = sample_id
        if task_id is not self._EMPTY_ID:
            updated_dict["task_id"] = task_id

        self._collection.update_one({"name": device_name}, {"$set": updated_dict})

    def set_running(self, device_name: str, *, task_id: ObjectId, sample_id: ObjectId):
        """
        Set a device's status to ``RUNNING``
        """
        self.set_status(device_name=device_name, status=DeviceStatus.RUNNING, task_id=task_id, sample_id=sample_id)

    def set_idle(self, device_name: str):
        """
        Set a device's status to ``IDLE`` and clear the sample_id and task_id in the device
        """
        self.set_status(device_name=device_name, status=DeviceStatus.IDLE, task_id=None, sample_id=None)

    def get_device_info(self, device_name: str) -> Dict[str, Any]:
        """
        Get all the information of a device stored in the database, which is generated at setting up stage.

        Args:
            device_name: the name of device

        Returns:
            A dict with all the device's information
        """
        device = self._collection.find_one({"name": device_name})
        if device is None:
            raise ValueError(f"No device with name: {device_name}")
        return device
