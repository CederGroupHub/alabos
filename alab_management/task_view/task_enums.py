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
    The status of one task.

    - ``WAITING``: the task cannot start yet, waiting for preceding tasks to finish
    - ``READY``: the task is ready to submit
    - ``INITIATED``: the task has been sent to task actor, but not yet running
    - ``REQUESTING_RESOURCES``: the task is requesting resources
    - ``RUNNING``: the task is currently running
    - ``FINISHING``: the task is finishing up, but not yet completed/errored/cancelled
    - ``ERROR``: the task encountered some errors during execution
    - ``COMPLETED``: the task is completed
    - ``CANCELLED``: the task has been cancelled and stopped.
    """

    WAITING = auto()
    READY = auto()
    INITIATED = auto()
    REQUESTING_RESOURCES = auto()
    RUNNING = auto()
    FINISHING = auto()
    ERROR = auto()
    COMPLETED = auto()
    CANCELLED = auto()
