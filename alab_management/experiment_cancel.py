"""Cancel one experiment and free only that experiment's software bookings.

This is the dashboard Cancel button. It force-cancels that experiment's live
tasks (the same write Release locks & tasks uses, scoped to this experiment),
dismisses its user-input prompts, cancels its pending resource requests,
releases its devices and positions, and marks the experiment Cancelled.

When ``mongodb_completed`` is configured, it then archives the experiment (and
its samples/tasks) into the completed database — the same copy step the
experiment manager runs when it marks an experiment finished.

It does not emergency-stop hardware that is already moving, and it does not
touch other experiments. Use Release locks & tasks when the whole lab is stuck.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from bson import ObjectId

from alab_management.config import AlabOSConfig
from alab_management.device_view.device_view import DeviceTaskStatus, DeviceView
from alab_management.experiment_view.completed_experiment_view import (
    CompletedExperimentView,
)
from alab_management.experiment_view.experiment_view import ExperimentStatus, ExperimentView
from alab_management.lab_reset import (
    LIVE_TASK_STATUSES,
    _abort_task_actor,
    prune_archived_unplaced_from_live,
)
from alab_management.resource_manager.enums import RequestStatus
from alab_management.sample_view.sample_view import SampleView
from alab_management.task_view.task_enums import CancelingProgress, TaskStatus
from alab_management.task_view.task_view import TaskView
from alab_management.user_input import CANCEL_RESPONSE, UserInputView
from alab_management.utils.data_objects import get_collection

logger = logging.getLogger(__name__)

OPEN_EXPERIMENT_STATUSES = {
    ExperimentStatus.PENDING.name,
    ExperimentStatus.RUNNING.name,
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

    tasks_cancelled = _force_cancel_experiment_tasks(task_view, task_ids, now)
    user_inputs_dismissed = user_input_view.dismiss_pending_requests(
        experiment_id=exp_id,
        response=CANCEL_RESPONSE,
        note="Dismissed because the experiment was cancelled.",
    )
    resource_requests_cancelled = _cancel_pending_resource_requests(task_ids)
    devices_released = _release_devices_held_by(device_view, task_ids, now)
    positions_unlocked = _unlock_positions_held_by(sample_view, task_ids)
    experiment_closed = _close_experiment(experiment_view, experiment)
    archived_to_completed = _archive_experiment_to_completed(exp_id)
    prune_summary = (
        prune_archived_unplaced_from_live() if archived_to_completed else {}
    )

    summary = {
        "tasks_cancelled": tasks_cancelled,
        "user_inputs_dismissed": user_inputs_dismissed,
        "resource_requests_cancelled": resource_requests_cancelled,
        "devices_released": devices_released,
        "positions_unlocked": positions_unlocked,
        "experiment_closed": experiment_closed,
        "archived_to_completed": archived_to_completed,
        **prune_summary,
    }
    logger.info("Cancelled experiment %s: %s", exp_id, summary)
    return summary


def _archive_experiment_to_completed(exp_id: ObjectId) -> bool:
    """Copy experiment + samples + tasks into ``Alab(completed)`` when configured.

    Matches ``ExperimentManager.mark_completed_experiments`` after a terminal
    status write. Also runs when Cancel is clicked on an already-cancelled
    experiment so orphans can be archived on retry.
    """
    if "mongodb_completed" not in AlabOSConfig():
        return False
    CompletedExperimentView().save_experiment(exp_id)
    logger.info(
        "Experiment (%s) and associated samples/tasks were copied to the completed db.",
        exp_id,
    )
    return True


def _force_cancel_experiment_tasks(
    task_view: TaskView, task_ids: list[ObjectId], now: datetime
) -> int:
    if not task_ids:
        return 0
    live_tasks = list(
        task_view._task_collection.find(
            {
                "_id": {"$in": task_ids},
                "status": {"$in": list(LIVE_TASK_STATUSES)},
            }
        )
    )
    for task in live_tasks:
        _abort_task_actor(task)
    if not live_tasks:
        return 0
    live_ids = [task["_id"] for task in live_tasks]
    task_view._task_collection.update_many(
        {"_id": {"$in": live_ids}},
        {
            "$set": {
                "status": TaskStatus.CANCELLED.name,
                "canceling_progress": CancelingProgress.WORKER_NOTIFIED.name,
                "message": "Cancelled via dashboard (Cancel Experiment).",
                "last_updated": now,
            }
        },
    )
    return len(live_ids)


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


def _close_experiment(experiment_view: ExperimentView, experiment: dict[str, Any]) -> bool:
    if experiment["status"] not in OPEN_EXPERIMENT_STATUSES:
        return False
    experiment_view.update_experiment_status(
        exp_id=experiment["_id"], status=ExperimentStatus.CANCELLED
    )
    return True
