r"""Force the lab back to an empty software state without restarting processes.

This is the dashboard "Release locks & tasks" action. It cancels every live task,
dismisses user-input prompts, drops resource locks, releases devices, clears the
mobile-robot queues, unlocks sample-position reservations, clears sample task
ownership / in-transit flags (without wiping physical ``position`` /
``last_position``), and closes open experiments.

It does not stop hardware that is already moving, and it does not drop Mongo.
"""

from __future__ import annotations

import logging
import time
from datetime import datetime
from typing import Any

from alab_management.config import AlabOSConfig
from alab_management.device_view.device_view import DevicePauseStatus, DeviceTaskStatus, DeviceView
from alab_management.experiment_view.completed_experiment_view import (
    CompletedExperimentView,
)
from alab_management.experiment_view.experiment_view import ExperimentStatus, ExperimentView
from alab_management.sample_view.sample_view import SampleView
from alab_management.task_view.task_enums import CancelingProgress, TaskStatus
from alab_management.task_view.task_view import TaskView
from alab_management.user_input import UserInputView, UserRequestStatus
from alab_management.utils.data_objects import get_collection, get_completed_collection

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

TERMINAL_EXPERIMENT_STATUSES = (
    ExperimentStatus.COMPLETED.name,
    ExperimentStatus.CANCELLED.name,
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


class LabNotIdleError(RuntimeError):
    """Raised when a lab-settings action requires an idle lab."""

    def __init__(self, reasons: list[str]):
        self.reasons = list(reasons)
        super().__init__(
            "Lab is not idle: " + "; ".join(self.reasons)
            if self.reasons
            else "Lab is not idle"
        )


def get_lab_idle_status() -> dict[str, Any]:
    """Return whether the lab has no live work or position reservations.

    Do not use ``/api/status`` alone — that endpoint only lists RUNNING experiments.
    """
    reasons: list[str] = []
    task_view = TaskView()
    live_tasks = task_view._task_collection.count_documents(
        {"status": {"$in": list(LIVE_TASK_STATUSES)}}
    )
    if live_tasks:
        reasons.append(f"{live_tasks} live task(s)")

    experiment_view = ExperimentView()
    for status_name in OPEN_EXPERIMENT_STATUSES:
        experiments = list(
            experiment_view.get_experiments_with_status(ExperimentStatus[status_name])
        )
        if experiments:
            reasons.append(
                f"{len(experiments)} {status_name.lower()} experiment(s)"
            )

    sample_view = SampleView()
    reserved = sample_view._sample_positions_collection.count_documents(
        {"task_id": {"$ne": None}}
    )
    if reserved:
        reasons.append(f"{reserved} reserved sample position(s)")

    return {"idle": not reasons, "reasons": reasons}


def clear_lab_occupancy() -> dict[str, int]:
    """Clear every sample's current position; keep identity, last_position, history.

    Requires an idle lab. Uses ``move_sample(..., None)`` so history gets a
    ``cleared`` event, matching per-slot Clear on Sample Positions.

    Archives any terminal live experiments that are missing from completed, then
    prunes live docs that are already archived (never deletes without a completed
    copy).
    """
    idle = get_lab_idle_status()
    if not idle["idle"]:
        raise LabNotIdleError(idle["reasons"])

    sample_view = SampleView()
    samples_cleared = 0
    for doc in sample_view._sample_collection.find({"position": {"$ne": None}}):
        sample_view.move_sample(doc["_id"], None)
        samples_cleared += 1

    in_transit_cleared = 0
    for doc in sample_view._sample_collection.find({"in_transit": {"$ne": None}}):
        sample_view.clear_sample_in_transit(doc["_id"])
        in_transit_cleared += 1

    positions_unlocked = _unlock_sample_positions(sample_view)
    experiments_archived = archive_terminal_experiments_missing_from_completed()
    prune_summary = prune_archived_unplaced_from_live()
    summary = {
        "samples_cleared": samples_cleared,
        "in_transit_cleared": in_transit_cleared,
        "positions_unlocked": positions_unlocked,
        "experiments_archived": experiments_archived,
        **prune_summary,
    }
    logger.info("Lab occupancy cleared: %s", summary)
    return summary


def archive_terminal_experiments_missing_from_completed() -> int:
    """Archive COMPLETED/CANCELLED live experiments that are not yet in completed."""
    if "mongodb_completed" not in AlabOSConfig():
        return 0
    try:
        completed_experiments = get_completed_collection("experiment")
    except ValueError:
        return 0

    experiment_view = ExperimentView()
    missing: list[Any] = []
    for experiment in experiment_view._experiment_collection.find(
        {"status": {"$in": list(TERMINAL_EXPERIMENT_STATUSES)}},
        projection={"_id": 1},
    ):
        exp_id = experiment["_id"]
        if completed_experiments.find_one({"_id": exp_id}, {"_id": 1}) is None:
            missing.append(exp_id)
    if not missing:
        return 0
    logger.info(
        "Archiving %s terminal live experiment(s) missing from completed before prune.",
        len(missing),
    )
    return archive_experiments_to_completed(missing)


def prune_archived_unplaced_from_live() -> dict[str, int]:
    """Delete live samples/tasks/experiments that are safely archived and unplaced.

    Hard rule: never delete a live document unless the same ``_id`` exists in
    ``Alab(completed)``. Missing completed copies are skipped with a warning.
    """
    empty = {
        "samples_pruned": 0,
        "tasks_pruned": 0,
        "experiments_pruned": 0,
        "skipped_not_in_completed": 0,
    }
    if "mongodb_completed" not in AlabOSConfig():
        return empty

    try:
        completed_samples = get_completed_collection("samples")
        completed_tasks = get_completed_collection("tasks")
        completed_experiments = get_completed_collection("experiment")
    except ValueError:
        logger.warning("Prune skipped: completed database is not available.")
        return empty

    sample_view = SampleView()
    task_view = TaskView()
    experiment_view = ExperimentView()
    live_samples = sample_view._sample_collection
    live_tasks = task_view._task_collection
    live_experiments = experiment_view._experiment_collection

    terminal_experiments = list(
        live_experiments.find({"status": {"$in": list(TERMINAL_EXPERIMENT_STATUSES)}})
    )

    samples_pruned = 0
    tasks_pruned = 0
    experiments_pruned = 0
    skipped = 0

    # Prune per terminal experiment as a unit: do not delete live samples while the
    # live experiment row still exists (dashboard /api/experiment/<id> would 500).
    for experiment in terminal_experiments:
        exp_id = experiment["_id"]
        if not completed_experiments.find_one({"_id": exp_id}, {"_id": 1}):
            skipped += 1
            logger.warning(
                "Prune skipped experiment %s: missing from Alab(completed).experiment.",
                exp_id,
            )
            continue

        sample_ids = [
            entry.get("sample_id")
            for entry in experiment.get("samples") or []
            if entry.get("sample_id") is not None
        ]
        live_sample_docs = (
            list(
                live_samples.find(
                    {"_id": {"$in": sample_ids}},
                    {"_id": 1, "position": 1, "in_transit": 1},
                )
            )
            if sample_ids
            else []
        )
        samples_ready = True
        for sample_doc in live_sample_docs:
            if sample_doc.get("position") is not None or sample_doc.get("in_transit") is not None:
                samples_ready = False
                break
            if not completed_samples.find_one({"_id": sample_doc["_id"]}, {"_id": 1}):
                samples_ready = False
                skipped += 1
                logger.warning(
                    "Prune skipped sample %s (experiment %s): missing from "
                    "Alab(completed).samples.",
                    sample_doc["_id"],
                    exp_id,
                )
                break
        if not samples_ready:
            continue

        task_ids = [
            task.get("task_id")
            for task in experiment.get("tasks") or []
            if task.get("task_id") is not None
        ]
        live_task_docs = (
            list(live_tasks.find({"_id": {"$in": task_ids}}, {"_id": 1}))
            if task_ids
            else []
        )
        all_tasks_safe = True
        for task_doc in live_task_docs:
            tid = task_doc["_id"]
            if not completed_tasks.find_one({"_id": tid}, {"_id": 1}):
                all_tasks_safe = False
                skipped += 1
                logger.warning(
                    "Prune skipped task %s (experiment %s): missing from Alab(completed).tasks.",
                    tid,
                    exp_id,
                )
        if not all_tasks_safe:
            # Do not delete the experiment until every remaining live task is archived.
            continue

        for sample_doc in live_sample_docs:
            live_samples.delete_one({"_id": sample_doc["_id"]})
            samples_pruned += 1

        for task_doc in live_task_docs:
            live_tasks.delete_one({"_id": task_doc["_id"]})
            tasks_pruned += 1

        # Re-check experiment still in completed immediately before delete
        if not completed_experiments.find_one({"_id": exp_id}, {"_id": 1}):
            skipped += 1
            logger.warning(
                "Prune skipped experiment %s at delete time: missing from completed.",
                exp_id,
            )
            continue
        live_experiments.delete_one({"_id": exp_id})
        experiments_pruned += 1

    summary = {
        "samples_pruned": samples_pruned,
        "tasks_pruned": tasks_pruned,
        "experiments_pruned": experiments_pruned,
        "skipped_not_in_completed": skipped,
    }
    if samples_pruned or tasks_pruned or experiments_pruned or skipped:
        logger.info("Pruned archived unplaced from live: %s", summary)
    return summary


def archive_experiments_to_completed(experiment_ids: list[Any]) -> int:
    """Copy each experiment into completed when configured. Returns how many archived."""
    if not experiment_ids or "mongodb_completed" not in AlabOSConfig():
        return 0
    archived = 0
    completed_view = CompletedExperimentView()
    for exp_id in experiment_ids:
        try:
            completed_view.save_experiment(exp_id)
            archived += 1
        except Exception:
            logger.exception("Failed to archive experiment %s to completed.", exp_id)
    return archived


def reset_lab_software_state(*, settle_s: float = DEFAULT_SETTLE_S) -> dict[str, int]:
    """Cancel everything the dashboard is waiting on so a new experiment can be submitted.

    Physical sample occupancy (``samples.position`` / ``last_position``) is preserved.
    Only ephemeral ownership is cleared: task IDs, in-transit flags, and position locks.
    Closed experiments are archived to completed when configured, then unplaced
    archived docs may be pruned from live.
    """
    task_view = TaskView()
    experiment_view = ExperimentView()
    device_view = DeviceView()
    sample_view = SampleView()
    user_input_view = UserInputView()
    now = datetime.now()

    # Capture open experiment ids before closing so we can archive them.
    to_archive: list[Any] = []
    for status in OPEN_EXPERIMENT_STATUSES:
        for experiment in experiment_view.get_experiments_with_status(
            ExperimentStatus[status]
        ):
            to_archive.append(experiment["_id"])

    tasks_cancelled = _cancel_live_tasks(task_view, now)
    user_inputs_dismissed = _dismiss_pending_experiment_user_inputs(user_input_view, now)
    if settle_s > 0:
        time.sleep(settle_s)
    _drop_resource_locks()
    devices_released = _release_devices(device_view, now)
    _clear_mobile_robot_queues(device_view)
    positions_unlocked = _unlock_sample_positions(sample_view)
    samples_unassigned = _clear_sample_ownership(sample_view, now)
    experiments_closed = _close_open_experiments(experiment_view)
    experiments_archived = archive_experiments_to_completed(to_archive)
    prune_summary = prune_archived_unplaced_from_live()

    summary = {
        "tasks_cancelled": tasks_cancelled,
        "user_inputs_dismissed": user_inputs_dismissed,
        "devices_released": devices_released,
        "positions_unlocked": positions_unlocked,
        "samples_unassigned": samples_unassigned,
        "experiments_closed": experiments_closed,
        "experiments_archived": experiments_archived,
        **prune_summary,
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
                "message": "Cancelled via dashboard (Release locks & tasks).",
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


def _dismiss_pending_experiment_user_inputs(
    user_input_view: UserInputView, now: datetime
) -> int:
    """Dismiss prompts that belong to an experiment, not Labman/maintenance refill requests."""
    result = user_input_view._input_collection.update_many(
        {
            "status": UserRequestStatus.PENDING.value,
            "request_context.experiment_id": {"$exists": True},
            "request_context.maintenance": {"$ne": True},
        },
        {
            "$set": {
                "status": UserRequestStatus.FULLFILLED.value,
                "response": "Reset",
                "note": "Dismissed by Release locks & tasks.",
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


def _clear_sample_ownership(sample_view: SampleView, now: datetime) -> int:
    """Clear ephemeral sample ownership; keep physical ``position`` / ``last_position``."""
    result = sample_view._sample_collection.update_many(
        {
            "$or": [
                {"task_id": {"$ne": None}},
                {"in_transit": {"$ne": None}},
            ]
        },
        {
            "$set": {
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
                exp_id=experiment["_id"], status=ExperimentStatus.CANCELLED
            )
            closed += 1
    return closed
