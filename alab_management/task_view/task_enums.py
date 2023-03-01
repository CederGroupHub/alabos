from enum import Enum, IntEnum, auto


class TaskPriority(IntEnum):
    """
    The priority of a task. larger integer = higher priority.

    Values >= 100 are reserved for urgent/error correcting resource requests.
    """

    SYSTEM = 900
    URGENT = 100
    HIGH = 30
    NORMAL = 20
    LOW = 10


class TaskStatus(Enum):
    """
    The status of one task

    - ``WAITING``: the task cannot start yet, waiting for preceding tasks to finish
    - ``INITIATED``: the task has been sent to task actor, but not yet running
    - ``PAUSED``: the task is paused by user
    - ``STOPPED``: the task has been stopped due to the system shutdown
    - ``READY``: the task is ready to submit
    - ``REQUESTING_RESOURCES``: the task is requesting resources
    - ``RUNNING``: the task is currently running
    - ``ERROR``: the task encountered some errors during execution
    - ``COMPLETED``: the task is completed
    - ``CANCELLING``: a cancelling request has been submitted
    - ``CANCELLED``: the task has been cancelled and stopped.
    """

    WAITING = auto()
    INITIATED = auto()
    PAUSED = auto()
    STOPPED = auto()
    READY = auto()
    REQUESTING_RESOURCES = auto()
    RUNNING = auto()
    ERROR = auto()
    COMPLETED = auto()
    CANCELLING = auto()
    CANCELLED = auto()
