from enum import Enum, auto

_EXTRA_REQUEST: str = "__nodevice"


class RequestStatus(Enum):
    """
    The status for a request. It will be stored in the database
    """

    PENDING = auto()
    FULFILLED = auto()
    NEED_RELEASE = auto()
    RELEASED = auto()
    CANCELED = auto()
    ERROR = auto()
