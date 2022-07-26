from enum import Enum, IntEnum, auto


class TaskPriority(IntEnum):
    """
    The priority of a task. larger integer = higher priority.

    Values >= 100 are reserved for urgent/error correcting resource requests.
    """

    URGENT = 100
    HIGH = 30
    NORMAL = 20
    LOW = 10


class TaskStatus(Enum):
    """
    The status of one task

    - ``WAITING``: the task cannot start now
    - ``READY``: the task is ready to submit
    - ``PAUSED``: the task is hold for a while
    - ``RUNNING``: the task is currently running
    - ``ERROR``: the task encountered some errors during execution
    - ``COMPLETED``: the task is completed
    """

    WAITING = auto()
    PAUSED = auto()
    STOPPED = auto()
    READY = auto()
    REQUESTING_RESOURCE = auto()
    RUNNING = auto()
    ERROR = auto()
    COMPLETED = auto()
