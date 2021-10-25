from enum import Enum, unique, auto


@unique
class DeviceStatus(Enum):
    UNKNOWN = auto()
    IDLE = auto()
    RUNNING = auto()
    ERROR = auto()
    HOLD = auto()
    STOPPED = auto()


class DeviceView:
    def get_status(self, device_name: str) -> DeviceStatus:
        ...

    def set_status(self, device_name: str, status: DeviceStatus):
        ...

    def get_device(self, name):
        ...
