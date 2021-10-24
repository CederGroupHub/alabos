from enum import Enum, unique, auto

from bson import ObjectId

from ..db import get_collection


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
