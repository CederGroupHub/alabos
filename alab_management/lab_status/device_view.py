from enum import Enum, unique, auto

from bson import ObjectId


@unique
class DeviceStatus(Enum):
    IDLE = auto()
    RUNNING = auto()
    ERROR = auto()
    HOLD = auto()
    STOPPED = auto()


class DeviceView:
    def get_status(self, device_id: ObjectId) -> DeviceStatus:
        ...

    def set_status(self, device_id: ObjectId, status: DeviceStatus):
        ...
