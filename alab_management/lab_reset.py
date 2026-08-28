"""Force the lab back to an empty software state without restarting processes.

This is the dashboard \"Reset lab\" button. It cancels every live task, dismisses
user-input prompts, drops resource locks, releases devices, clears the mobile-robot
queues, unassigns samples from positions, and closes open experiments.

It does not stop hardware that is already moving, and it does not drop Mongo.
"""

from __future__ import annotations

import logging
import time
from datetime import datetime
from typing import Any

from alab_management.device_view.device_view import DevicePauseStatus, DeviceTaskStatus, DeviceView
from alab_management.experiment_view.experiment_view import ExperimentStatus, ExperimentView
from alab_management.sample_view.sample_view import SampleView
from alab_management.task_view.task_enums import CancelingProgress, TaskStatus
from alab_management.task_view.task_view import TaskView
from alab_management.user_input import UserInputView, UserRequestStatus
from alab_management.utils.data_objects import get_collection

logger = logging.getLogger(__name__)

LIVE_TASK_STATUSES = (
    TaskStatus.WAITING.name,
    TaskStatus.READY.name,
    TaskStatus.INITIATED.name,
    TaskStatus.REQUESTING_RESOURCES.name,
    TaskStatus.RUNNING.name,
    TaskStatus.FINISHING.name,
)

OPEN_EXPERIMENT_STATUSES = (
    ExperimentStatus.PENDING.name,
    ExperimentStatus.RUNNING.name,
)

MOBILE_ROBOT_QUEUE_ATTRIBUTES = {
    "pending_requests": {},
    "in_progress_requests": {},
    "executing_plan_status": "idle",
    "executing_subracks_source_to_base_mapping": {},
    "executing_sample_position_from_source_to_base_mapping": {},
    "executing_sample_position_from_base_to_destination_mapping": {},
    "pre_mission_home": {},
    "recovery_handler_running": False,
    "recovery_handler_request_id": None,
    "critical_battery_handler_running": False,
    "critical_battery_handler_request_id": None,
    "touched_something_recovery_handler_running": False,
    "touched_something_recovery_handler_request_id": None,
    "failed_to_calibrate_tag_recovery_handler_running": False,
    "failed_to_calibrate_tag_recovery_handler_request_id": None,
}

DEFAULT_SETTLE_S = 2.0


def reset_lab_software_state(*, settle_s: float = DEFAULT_SETTLE_S) -> dict[str, int]:
    """Cancel everything the dashboard is waiting on so a new experiment can be submitted."""
    task_view = TaskView()
    experiment_view = ExperimentView()
    device_view = DeviceView()
    sample_view = SampleView()
    user_input_view = UserInputView()
    now = datetime.now()

    tasks_cancelled = _cancel_live_tasks(task_view, now)
    user_inputs_dismissed = _dismiss_pending_user_inputs(user_input_view, now)
    if settle_s > 0:
        time.sleep(settle_s)
    _drop_resource_locks()
    devices_released = _release_devices(device_view, now)
    _clear_mobile_robot_queues(device_view)
    positions_unlocked = _unlock_sample_positions(sample_view)
    samples_unassigned = _unassign_samples(sample_view, now)
    experiments_closed = _close_open_experiments(experiment_view)

    summary = {
        "tasks_cancelled": tasks_cancelled,
        "user_inputs_dismissed": user_inputs_dismissed,
        "devices_released": devices_released,
        "positions_unlocked": positions_unlocked,
        "samples_unassigned": samples_unassigned,
        "experiments_closed": experiments_closed,
    }
    logger.info("Lab software reset: %s", summary)
    return summary


def _cancel_live_tasks(task_view: TaskView, now: datetime) -> int:
    live_tasks = list(
        task_view._task_collection.find({"status": {"$in": list(LIVE_TASK_STATUSES)}})
    )
    for task in live_tasks:
        _abort_task_actor(task)
    if not live_tasks:
        return 0
    task_ids = [task["_id"] for task in live_tasks]
    task_view._task_collection.update_many(
        {"_id": {"$in": task_ids}},
        {
            "$set": {
                "status": TaskStatus.CANCELLED.name,
                "canceling_progress": CancelingProgress.WORKER_NOTIFIED.name,
                "message": "Cancelled by Reset lab.",
                "last_updated": now,
            }
        },
    )
    return len(task_ids)


def _abort_task_actor(task: dict[str, Any]) -> None:
    message_id = task.get("task_actor_id")
    if not message_id:
        return
    try:
        from dramatiq_abort import abort, abort_requested

        if abort_requested(message_id=message_id) is None:
            abort(message_id=message_id)
    except Exception:
        logger.warning(
            "Could not abort Dramatiq message %s for task %s",
            message_id,
            task.get("_id"),
            exc_info=True,
        )


def _dismiss_pending_user_inputs(user_input_view: UserInputView, now: datetime) -> int:
    result = user_input_view._input_collection.update_many(
        {"status": UserRequestStatus.PENDING.value},
        {
            "$set": {
                "status": UserRequestStatus.FULLFILLED.value,
                "response": "Reset",
                "note": "Dismissed by Reset lab.",
                "last_updated": now,
            }
        },
    )
    return result.modified_count


def _drop_resource_locks() -> None:
    get_collection("_lock").drop()
    get_collection("requests").drop()


def _release_devices(device_view: DeviceView, now: datetime) -> int:
    released = 0
    for device in device_view._device_collection.find():
        attributes = device.get("attributes") or {}
        update: dict[str, Any] = {
            "task_id": None,
            "last_updated": now,
        }
        if attributes.get("disabled"):
            update["status"] = device.get("status") or DeviceTaskStatus.IDLE.name
        else:
            update["status"] = DeviceTaskStatus.IDLE.name
            update["pause_status"] = DevicePauseStatus.RELEASED.name
        device_view._device_collection.update_one(
            {"_id": device["_id"]}, {"$set": update}
        )
        released += 1
    return released


def _clear_mobile_robot_queues(device_view: DeviceView) -> None:
    for device in device_view._device_collection.find():
        attributes = dict(device.get("attributes") or {})
        if not any(key in attributes for key in MOBILE_ROBOT_QUEUE_ATTRIBUTES):
            continue
        attributes.update(MOBILE_ROBOT_QUEUE_ATTRIBUTES)
        device_view._device_collection.update_one(
            {"_id": device["_id"]},
            {"$set": {"attributes": attributes}},
        )


def _unlock_sample_positions(sample_view: SampleView) -> int:
    result = sample_view._sample_positions_collection.update_many(
        {"task_id": {"$ne": None}},
        {"$set": {"task_id": None}},
    )
    return result.modified_count


def _unassign_samples(sample_view: SampleView, now: datetime) -> int:
    result = sample_view._sample_collection.update_many(
        {
            "$or": [
                {"position": {"$ne": None}},
                {"task_id": {"$ne": None}},
                {"in_transit": {"$ne": None}},
            ]
        },
        {
            "$set": {
                "position": None,
                "task_id": None,
                "in_transit": None,
                "last_updated": now,
            }
        },
    )
    return result.modified_count


def _close_open_experiments(experiment_view: ExperimentView) -> int:
    closed = 0
    for status in OPEN_EXPERIMENT_STATUSES:
        experiments = list(
            experiment_view.get_experiments_with_status(ExperimentStatus[status])
        )
        for experiment in experiments:
            experiment_view.update_experiment_status(
                exp_id=experiment["_id"], status=ExperimentStatus.COMPLETED
            )
            closed += 1
    return closed
