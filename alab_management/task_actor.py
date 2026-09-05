"""
The ``run_task`` function is used to launch a task in the dramatiq worker. It will be called by the ``task_manager``.
The function will update the status of the task in the database and initiate the task with proper parameters.
"""

import datetime
import logging
from traceback import format_exc

import dramatiq
from bson import ObjectId
from dramatiq_abort import Abort
from pydantic import BaseModel, ValidationError

from alab_management.logger import DBLogger
from alab_management.sample_view import SampleView
from alab_management.task_view import BaseTask, TaskStatus, TaskView
from alab_management.task_view.task import TaskCancelledError
from alab_management.utils.data_objects import get_rabbitmq_broker
from alab_management.utils.error_context import format_error_report, get_error_origin
from alab_management.utils.logger import configure_logging
from alab_management.utils.middleware import register_abortable_middleware
from alab_management.utils.module_ops import load_definition

configure_logging(
    dramatiq_level=logging.INFO,
    mobile_robot_debug=False,
    robot_arm_mobile_debug=False,
    announce=False,
)

dramatiq.set_broker(get_rabbitmq_broker())

register_abortable_middleware()

cli_logger = logging.getLogger(__name__)


@dramatiq.actor(
    max_retries=0,
    time_limit=30 * 24 * 60 * 60 * 1000,
    notify_shutdown=True,
)  # time limit is set in ms. currently set to 30 days
def run_task(task_id_str: str):
    """Submit a task. In this system, each task is run in an
    independent process, which will try to acquire device and
    process samples. This will change the status of the task under the specified id into "RUNNING".
    If the task is not in "INITIATED" state, it has been picked up by another task actor beforehand,
    and no action is taken.
    If an Abort (exception) signal is sent, the task status will be changed to "CANCELLED".
    If a Shutdown (exception) signal is sent, the task status will be changed to "STOPPED".
    If any other exception is raised, the task status will be changed to "ERROR".
    If there is no exception raised, once the task is completed, the status will be changed to "COMPLETED".
    Sample task id will be set to None after the task is completed.

    Args:
        task_id_str: The id of the task to run.
    """
    cli_logger.info(f"Worker starts the task with id: {task_id_str}.")
    from alab_management.config import AlabOSConfig

    from .lab_view import LabView  # pylint: disable=cyclic-import

    config = AlabOSConfig()
    reload = config["general"].get("auto_refresh", False)
    load_definition(reload=reload)
    task_view = TaskView()
    sample_view = SampleView()
    logger = DBLogger(task_id=None)

    task_id = ObjectId(task_id_str)
    try:
        task_entry = task_view.get_task(task_id, encode=True)
    except ValueError:
        cli_logger.info(f'{datetime.datetime.now()}: No task found with id: {task_id} -- assuming that alabos was aborted without cleanup, and skipping this task.')
        return

    if task_view.get_status(task_id) != TaskStatus.INITIATED:
        cli_logger.info('Task status is not INITIATED; this implies the task has already been picked up by a previous task actor. No action is taken.')
        return

    try:
        task_type = task_entry.pop("type")
        cli_logger.info(f'{datetime.datetime.now()}: Worker picked up task {task_id} of type {task_type.__name__}')
    except ValueError:
        cli_logger.info(f'{datetime.datetime.now()}: No task found with id: {task_id} -- assuming that alabos was aborted without cleanup, and skipping this task.')
        return

    lab_view = LabView(task_id=task_id)

    try:
        task: BaseTask = task_type(
            samples=[
                sample["name"] for sample in task_entry["samples"]
            ],  # only the sample names are sent
            task_id=task_id,
            lab_view=lab_view,
            _offline_mode=False,
            **task_entry["parameters"],
        )
        if not task.validate():
            raise ValueError(
                f"Task input validation failed! Error message: {task.get_message()}"
            )
    except Exception as exception:
        task_view.update_status(task_id=task_id, status=TaskStatus.FINISHING)
        origin = get_error_origin(exception)
        error_report = format_error_report(
            exc=exception,
            task_type=task_type.__name__,
            task_id=task_id,
            samples=[sample["name"] for sample in task_entry["samples"]],
            header="Task could not be created",
        )
        # Surface the rich error on the dashboard task message as well.
        task_view.set_message(task_id=task_id, message=error_report)
        logger.system_log(
            level="ERROR",
            log_data={
                "logged_by": "TaskActor",
                "type": "TaskDefinition",
                "task_id": task_id,
                "task_type": task_type.__name__,
                "message": str(exception),
                "error_type": origin["exc_type"],
                "error_message": origin["exc_message"],
                "error_location": origin["raised_at_str"],
                "error_project_location": origin["project_frame_str"],
                "traceback": error_report,
            },
        )
        lab_view.request_cleanup(error_message=error_report)
        raise Exception(
            f"Failed to create task {task_id} of type {task_type!s}"
        ) from exception
    finally:
        # if there is early termination, set the task status to ERROR
        if task_view.get_status(task_id) == TaskStatus.FINISHING:
            task_view.update_status(task_id=task_id, status=TaskStatus.ERROR)

    try:
        task_view.update_status(task_id=task_id, status=TaskStatus.RUNNING)
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
        cli_logger.debug(f"Task {task_id} of type {task_type.__name__} is running.")
        # Following is the line of code that actually runs the task
        # from Alab_one, for eg: Powder dosing. Powder dosing class will have a method "run".
        result = task.run()
    # A task that stopped itself because it was asked to is cancelled, not broken. Both arrive
    # here: `Abort` when the worker thread could be interrupted, `TaskCancelledError` when it
    # could not and the task had to bail out of a blocking call by itself.
    except (Abort, TaskCancelledError) as cancellation:
        task_status = TaskStatus.CANCELLED
        reason = (
            str(cancellation)
            if isinstance(cancellation, TaskCancelledError) and str(cancellation)
            else "Task was cancelled due to the abort signal"
        )
        task_view.update_status(task_id=task_id, status=TaskStatus.FINISHING)
        task_view.set_message(
            task_id=task_id, message=reason
        )  # display exception on the dashboard
        logger.system_log(
            level="ERROR",
            log_data={
                "logged_by": "TaskActor",
                "type": "TaskEnd",
                "task_id": task_id,
                "task_type": task_type.__name__,
                "status": TaskStatus.CANCELLED.name,
                "traceback": reason,
            },
        )
        cli_logger.info(f"Task {task_type} ({task_id}) was cancelled: {reason}")
        # Give the task a chance to stop hardware and reconcile its samples while it still holds its
        # resources. A failure here must not leave the task stuck part-way through cancelling, so it
        # is logged and cancellation continues regardless.
        try:
            task.on_cancel()
        except Exception as cancel_exception:  # noqa: BLE001
            cancel_report = format_error_report(
                exc=cancel_exception,
                task_type=task_type.__name__,
                task_id=task_id,
                samples=[sample["name"] for sample in task_entry["samples"]],
                header="on_cancel failed while cancelling the task",
            )
            task_view.set_message(task_id=task_id, message=cancel_report)
            logger.system_log(
                level="ERROR",
                log_data={
                    "logged_by": "TaskActor",
                    "type": "TaskCancelCleanup",
                    "task_id": task_id,
                    "task_type": task_type.__name__,
                    "message": str(cancel_exception),
                    "traceback": cancel_report,
                },
            )
            cli_logger.error(
                f"on_cancel of task {task_type} ({task_id}) failed: {cancel_exception}"
            )
        # Do not prompt the operator to remove samples. Free their booked occupancy while
        # retaining last-known and in-transit evidence, then release task resources.
        lab_view.release_samples_occupancy(
            task_entry["samples"], reason="Task was cancelled"
        )
        lab_view.release_all_resources()
    except:  # noqa: E722
        task_status = TaskStatus.ERROR
        task_view.update_status(task_id=task_id, status=TaskStatus.FINISHING)
        # Capture the process stage (the task's last status message) before we overwrite it.
        try:
            stage = task.get_message()
        except Exception:  # noqa: BLE001
            stage = None
        origin = get_error_origin()
        formatted_exception = format_exc()
        error_report = format_error_report(
            task_type=task_type.__name__,
            task_id=task_id,
            samples=[sample["name"] for sample in task_entry["samples"]],
            stage=stage,
            header="Task failed",
        )
        task_view.set_message(
            task_id=task_id, message=error_report
        )  # display rich error on the dashboard
        logger.system_log(
            level="ERROR",
            log_data={
                "logged_by": "TaskActor",
                "type": "TaskEnd",
                "task_id": task_id,
                "task_type": task_type.__name__,
                "status": "ERROR",
                "stage": stage,
                "error_type": origin["exc_type"],
                "error_message": origin["exc_message"],
                "error_location": origin["raised_at_str"],
                "error_project_location": origin["project_frame_str"],
                "traceback": formatted_exception,
            },
        )
        cli_logger.error(
            f"Task {task_type} ({task_id}) failed: {origin['exc_type']}: {origin['exc_message']} "
            f"at {origin['raised_at_str']} (stage: {stage})"
        )
        lab_view.request_cleanup(error_message=error_report)
    else:
        task_status = TaskStatus.COMPLETED
        task_view.update_status(task_id=task_id, status=TaskStatus.FINISHING)
        if result is None:
            pass
        elif isinstance(result, BaseModel):
            # assume that all field are replaced by the value if the result is a pydantic model
            # convert pydantic model to dict
            dict_result = result.model_dump(mode="python")
            for key, value in dict_result.items():
                task_view.update_result(task_id=task_id, name=key, value=value)
        elif isinstance(result, dict):
            for key, value in result.items():
                # we do this per item to avoid overwriting existing results. Its possible that some results were
                # uploaded mid-task under different keys using lab_view.update_result()
                task_view.update_result(task_id=task_id, name=key, value=value)
        else:
            task_view.update_result(
                task_id=task_id, name=None, value=result
            )  # put result directly in the result field, no nesting.

        # if the task result specification is defined,
        # check if the task result is consistent with the task result specification
        # get result from the task entry
        if task.result_specification is not None:
            result = task_view.get_task(task_id=task_id).get("result", {})
            if isinstance(result, dict):
                try:
                    model = task.result_specification
                    model(**result)
                except ValidationError:
                    cli_logger.warning(f'WARNING: Task result for task_id {task_id_str} is inconsistent with the task result specification.{format_exc()}')
                    cli_logger.info("")
            else:
                cli_logger.warning(f'WARNING: Task result for task_id {task_id_str} is not a dictionary, but a {type(result)}.Therefore, the task result specification is invalid. Please ensure that the task result is a dictionary.')

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
        cli_logger.info(f"Task {task_type} ({task_id}) completed successfully.")
    finally:
        for sample in task_entry["samples"]:
            sample_view.update_sample_task_id(
                task_id=None, sample_id=sample["sample_id"]
            )
        task_view.update_status(task_id=task_id, status=task_status)
