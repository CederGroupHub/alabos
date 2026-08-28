"""Cancel one experiment and free only that experiment's software bookings.

This is the dashboard Cancel button. It marks the experiment's tasks for
cancellation, dismisses that experiment's user-input prompts, cancels its
pending resource requests, and closes the experiment once every task is
terminal.

It does not emergency-stop hardware that is already moving, and it does not
touch other experiments. Use Reset lab when the whole lab is stuck.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from bson import ObjectId

from alab_management.device_view.device_view import DeviceTaskStatus, DeviceView
from alab_management.experiment_view.experiment_view import ExperimentStatus, ExperimentView
from alab_management.resource_manager.enums import RequestStatus
from alab_management.sample_view.sample_view import SampleView
from alab_management.task_view.task_enums import TaskStatus
from alab_management.task_view.task_view import TaskView
from alab_management.user_input import CANCEL_RESPONSE, UserInputView
from alab_management.utils.data_objects import get_collection

logger = logging.getLogger(__name__)

TERMINAL_TASK_STATUSES = {
    TaskStatus.COMPLETED.name,
    TaskStatus.ERROR.name,
    TaskStatus.CANCELLED.name,
}


def cancel_experiment_software_state(exp_id: ObjectId) -> dict[str, Any]:
    """Stop one experiment and release the bookings that belong to it."""
    task_view = TaskView()
    experiment_view = ExperimentView()
    device_view = DeviceView()
    sample_view = SampleView()
    user_input_view = UserInputView()
    now = datetime.now()

    experiment = experiment_view.get_experiment(exp_id)
    if experiment is None:
        raise ValueError(f"Experiment not found: {exp_id}")

    task_ids = [
        task["task_id"]
        for task in experiment.get("tasks", [])
        if task.get("task_id") is not None
    ]

    tasks_marked = 0
    for task_id in task_ids:
        if task_view.mark_task_as_canceling(task_id):
            tasks_marked += 1

    user_inputs_dismissed = user_input_view.dismiss_pending_requests(
        experiment_id=exp_id,
        response=CANCEL_RESPONSE,
        note="Dismissed because the experiment was cancelled.",
    )
    resource_requests_cancelled = _cancel_pending_resource_requests(task_ids)

    cancelled_task_ids = [
        task_id
        for task_id in task_ids
        if task_view.get_status(task_id).name == TaskStatus.CANCELLED.name
    ]
    devices_released = _release_devices_held_by(device_view, cancelled_task_ids, now)
    positions_unlocked = _unlock_positions_held_by(sample_view, cancelled_task_ids)

    experiment_closed = _close_experiment_if_terminal(
        experiment_view, task_view, experiment, task_ids
    )

    summary = {
        "tasks_marked": tasks_marked,
        "user_inputs_dismissed": user_inputs_dismissed,
        "resource_requests_cancelled": resource_requests_cancelled,
        "devices_released": devices_released,
        "positions_unlocked": positions_unlocked,
        "experiment_closed": experiment_closed,
    }
    logger.info("Cancelled experiment %s: %s", exp_id, summary)
    return summary


def _cancel_pending_resource_requests(task_ids: list[ObjectId]) -> int:
    if not task_ids:
        return 0
    result = get_collection("requests").update_many(
        {
            "task_id": {"$in": task_ids},
            "status": RequestStatus.PENDING.name,
        },
        {"$set": {"status": RequestStatus.CANCELED.name}},
    )
    return result.modified_count


def _release_devices_held_by(
    device_view: DeviceView, task_ids: list[ObjectId], now: datetime
) -> int:
    if not task_ids:
        return 0
    result = device_view._device_collection.update_many(
        {"task_id": {"$in": task_ids}},
        {
            "$set": {
                "task_id": None,
                "status": DeviceTaskStatus.IDLE.name,
                "last_updated": now,
            }
        },
    )
    return result.modified_count


def _unlock_positions_held_by(sample_view: SampleView, task_ids: list[ObjectId]) -> int:
    if not task_ids:
        return 0
    result = sample_view._sample_positions_collection.update_many(
        {"task_id": {"$in": task_ids}},
        {"$set": {"task_id": None}},
    )
    return result.modified_count


def _close_experiment_if_terminal(
    experiment_view: ExperimentView,
    task_view: TaskView,
    experiment: dict[str, Any],
    task_ids: list[ObjectId],
) -> bool:
    if experiment["status"] == ExperimentStatus.COMPLETED.name:
        return False

    # A PENDING experiment may not have task ids yet. Closing it here is what
    # stops Experiment Manager from starting it after Cancel.
    if experiment["status"] == ExperimentStatus.PENDING.name and not task_ids:
        experiment_view.update_experiment_status(
            exp_id=experiment["_id"], status=ExperimentStatus.COMPLETED
        )
        return True

    if task_ids and all(
        task_view.get_status(task_id).name in TERMINAL_TASK_STATUSES
        for task_id in task_ids
    ):
        experiment_view.update_experiment_status(
            exp_id=experiment["_id"], status=ExperimentStatus.COMPLETED
        )
        return True
    return False
