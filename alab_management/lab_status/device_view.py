from enum import Enum, unique, auto
from typing import Union, Dict, Any, Optional

from bson import ObjectId

from alab_management.config import config
from alab_management.db import get_collection


@unique
class DeviceStatus(Enum):
    UNKNOWN = auto()
    IDLE = auto()
    RUNNING = auto()
    ERROR = auto()
    HOLD = auto()
    STOPPED = auto()


class DeviceView:
    def __init__(self):
        self._collection = get_collection(config["devices"]["device_db"])

    def get_status(self, device_name: str) -> DeviceStatus:
        return DeviceStatus[self.get_device_info(device_name=device_name)["status"]]

    def set_status(self, device_name: str,
                   status: Union[DeviceStatus, str],
                   *,
                   sample_id: Optional[ObjectId] = ...,
                   task_id: Optional[ObjectId] = ...):
        if isinstance(status, DeviceStatus):
            status = status.name
        updated_dict = {
            "status": status,
        }

        if sample_id is not ...:
            updated_dict["sample_id"] = sample_id
        if task_id is not ...:
            updated_dict["task_id"] = task_id

        self._collection.update_one({"name": device_name}, {"$set": updated_dict})

    def set_running(self, device_name: str, *, task_id: ObjectId, sample_id: ObjectId):
        self.set_status(device_name=device_name, status=DeviceStatus.RUNNING, task_id=task_id, sample_id=sample_id)

    def set_idle(self, device_name: str, *, task_id: ObjectId, sample_id: ObjectId):
        self.set_status(device_name=device_name, status=DeviceStatus.IDLE, task_id=task_id, sample_id=sample_id)

    def get_device_info(self, device_name: str) -> Dict[str, Any]:
        device = self._collection.find_one({"name": device_name})
        if device is None:
            raise ValueError(f"No device with name: {device_name}")
        return device
