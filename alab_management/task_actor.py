"""
The ``run_task`` function is used to launch a task in the dramatiq worker. It will be called by the ``task_manager``.
The function will update the status of the task in the database and initiate the task with proper parameters.
"""

from traceback import format_exc

import dramatiq
from bson import ObjectId

from alab_management.logger import DBLogger
from alab_management.sample_view import SampleView

# from alab_management.task_view.task import BaseTask
# from alab_management.task_view.task_view import TaskView
from alab_management.task_view import BaseTask, TaskView, TaskStatus
from alab_management.utils.module_ops import load_definition


class ParameterError(Exception):
    """
    The exception raised when parameters of a task is wrong
    """


@dramatiq.actor(max_retries=0)
def run_task(task_id_str: str):
    """
    Submit a task. In this system, each task is run in an
    independent process, which will try to acquire device and
    process samples.
    """
    from .lab_view import LabView  # pylint: disable=cyclic-import

    load_definition()
    task_view = TaskView()
    sample_view = SampleView()
    logger = DBLogger(task_id=None)

    task_id = ObjectId(task_id_str)
    task_entry = task_view.get_task(task_id, encode=True)
    if task_entry is None:
        raise ValueError(f"Cannot find task with task id: {task_id}")
    task_type = task_entry.pop("type")

    try:
        task: BaseTask = task_type(
            task_id=task_id,
            lab_view=LabView(task_id=task_id),
            sample=list(task_entry["samples"].values()),  # only the ObjectId's are sent
            # **task_entry["samples"],
            **task_entry["parameters"],
        )
    except Exception as exception:
        logger.system_log(
            level="ERROR",
            log_data={
                "logged_by": "TaskActor",
                "type": "TaskDefinition",
                "task_id": task_id,
                "task_type": task_type.__name__,
                "message": str(exception),
            },
        )
        raise Exception(
            "Failed to create task {} of type {}".format(task_id, str(task_type))
        )
        # raise ParameterError(exception.args[0]) from exception

    task_view.update_status(task_id=task_id, status=TaskStatus.RUNNING)
    for sample_id in task_entry["samples"].values():
        sample_view.update_sample_task_id(task_id=task_id, sample_id=sample_id)

    logger.system_log(
        level="INFO",
        log_data={
            "logged_by": "TaskActor",
            "type": "TaskStart",
            "task_id": task_id,
            "task_type": task_type.__name__,
        },
    )

    try:
        result = task.run()
    except Exception:
        task_view.update_status(task_id=task_id, status=TaskStatus.ERROR)
        logger.system_log(
            level="ERROR",
            log_data={
                "logged_by": "TaskActor",
                "type": "TaskEnd",
                "task_id": task_id,
                "task_type": task_type.__name__,
                "status": "ERROR",
                "traceback": format_exc(),
            },
        )
        raise
    else:
        task_view.update_status(task_id=task_id, status=TaskStatus.COMPLETED)
        task_view.update_result(task_id=task_id, task_result=result)
        logger.system_log(
            level="INFO",
            log_data={
                "logged_by": "TaskActor",
                "type": "TaskEnd",
                "task_id": task_id,
                "task_type": task_type.__name__,
                "status": "COMPLETED",
            },
        )
    finally:
        for sample_id in task_entry["samples"].values():
            sample_view.update_sample_task_id(task_id=None, sample_id=sample_id)
