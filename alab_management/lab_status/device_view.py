from dataclasses import asdict
from enum import Enum, unique, auto
from pathlib import Path

from bson import ObjectId

from ..config import config
from ..db import get_collection
from ..device_def.base_device import get_all_devices, add_device


@unique
class DeviceStatus(Enum):
    UNKNOWN = auto()
    IDLE = auto()
    RUNNING = auto()
    ERROR = auto()
    HOLD = auto()
    STOPPED = auto()


class DeviceView:
    device_collection = get_collection("devices")

    def get_status(self, device_id: ObjectId) -> DeviceStatus:
        ...

    def set_status(self, device_id: ObjectId, status: DeviceStatus):
        ...
