"""Operator-facing reasons for tasks that are not yet running."""

from alab_management.task_view.task_enums import TaskStatus

WORKER_QUEUE_MESSAGE = (
    "Queued for a worker process. This starts automatically when a worker is free; "
    "nothing is dropped. If it stays queued for a long time, the workers may be busy "
    "or not running."
)

DEFAULT_WAIT_MESSAGES = {
    TaskStatus.WAITING.name: "Waiting for a previous task in this experiment to finish.",
    TaskStatus.READY.name: "Ready to run. Waiting to be sent to a worker queue.",
    TaskStatus.INITIATED.name: WORKER_QUEUE_MESSAGE,
    TaskStatus.REQUESTING_RESOURCES.name: (
        "A worker has this task. Waiting for a lab device or sample position to become free."
    ),
}


def default_wait_message(status: str | TaskStatus, existing: str = "") -> str:
    """Return the stored message, or a status-based wait reason if it is empty."""
    if (existing or "").strip():
        return existing.strip()
    name = status.name if isinstance(status, TaskStatus) else str(status or "")
    return DEFAULT_WAIT_MESSAGES.get(name, "")
