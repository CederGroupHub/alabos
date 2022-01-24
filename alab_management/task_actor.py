from traceback import format_exc

import dramatiq
from bson import ObjectId

from .lab_manager import LabManager
from .logger import DBLogger
from .sample_view import SampleView
from .task_view.task import BaseTask
from .task_view.task_view import TaskView, TaskStatus
from .utils.module_ops import load_definition


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
            lab_manager=LabManager(task_id=task_id),
            **task_entry["samples"],
            **task_entry["parameters"],
        )
    except AttributeError as exception:
        raise ParameterError(exception.args[0]) from exception

    task_view.update_status(task_id=task_id, status=TaskStatus.RUNNING)
    for sample_id in task_entry["samples"].values():
        sample_view.update_sample_task_id(task_id=task_id, sample_id=sample_id)

    try:
        task.run()
    except Exception:
        task_view.update_status(task_id=task_id, status=TaskStatus.ERROR)
        logger.system_log(level="ERROR",
                          log_data={
                              "logged_by": "TaskActor",
                              "type": "TaskEnd",
                              "task_id": task_id,
                              "task_type": task_type.__name__,
                              "status": "ERROR",
                              "traceback": format_exc(),
                          })
        raise
    else:
        task_view.update_status(task_id=task_id, status=TaskStatus.COMPLETED)
        logger.system_log(level="INFO",
                          log_data={
                              "logged_by": "TaskActor",
                              "type": "TaskEnd",
                              "task_id": task_id,
                              "task_type": task_type.__name__,
                              "status": "COMPLETED",
                          })
    finally:
        for sample_id in task_entry["samples"].values():
            sample_view.update_sample_task_id(task_id=None, sample_id=sample_id)

    logger.system_log(level="INFO",
                      log_data={
                          "type": "TaskStart",
                          "task_id": task_id,
                          "task_type": task_type.__name__
                      })
