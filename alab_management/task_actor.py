"""
The ``run_task`` function is used to launch a task in the dramatiq worker. It will be called by the ``task_manager``.
The function will update the status of the task in the database and initiate the task with proper parameters.
"""

import datetime
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


@dramatiq.actor(
    max_retries=0, time_limit=48*60*60*1000, 
)  # TODO time limit is set in ms. currently set to 48 hours
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
    try:
        task_entry = task_view.get_task(task_id, encode=True)
        task_type = task_entry.pop("type")
        print(f"{datetime.datetime.now()}: Worker picked up task {task_id} of type {task_type.__name__}")
    except ValueError:
        print(
            f"{datetime.datetime.now()}: No task found with id: {task_id} -- assuming that alabos was aborted without cleanup, and skipping this task."
        )
        return

    try:
        task: BaseTask = task_type(
            task_id=task_id,
            lab_view=LabView(task_id=task_id),
            # samples=[
            #     sample["sample_id"] for sample in task_entry["samples"]
            # ],  # only the sample ObjectId's are sent
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

    for sample in task_entry["samples"]:
        sample_view.update_sample_task_id(
            task_id=task_id, sample_id=sample["sample_id"]
        )

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
        task_view.update_status(task_id=task_id, status=TaskStatus.RUNNING)
        result = task.run()
    except Exception:
        task_view.update_status(task_id=task_id, status=TaskStatus.ERROR)
        formatted_exception = format_exc()
        task_view.set_message(
            task_id=task_id, message=formatted_exception
        )  # display exception on the dashboard
        logger.system_log(
            level="ERROR",
            log_data={
                "logged_by": "TaskActor",
                "type": "TaskEnd",
                "task_id": task_id,
                "task_type": task_type.__name__,
                "status": "ERROR",
                "traceback": formatted_exception,
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
        for sample in task_entry["samples"]:
            sample_view.update_sample_task_id(
                task_id=None, sample_id=sample["sample_id"]
            )
