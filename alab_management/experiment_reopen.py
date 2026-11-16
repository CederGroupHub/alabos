"""Reopen a cancelled/errored experiment from a chosen task (checkpoint resume)."""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from bson import ObjectId  # type: ignore

from alab_management.experiment_view.experiment_view import (
    ExperimentStatus,
    ExperimentView,
)
from alab_management.sample_view.sample_view import SampleView
from alab_management.task_view.task_enums import CancelingProgress, TaskStatus
from alab_management.task_view.task_view import TaskView
from alab_management.utils.data_objects import get_collection

logger = logging.getLogger(__name__)

_TERMINAL_TASK = {TaskStatus.ERROR, TaskStatus.CANCELLED, TaskStatus.COMPLETED}
_LIVE_TASK = {
    TaskStatus.WAITING,
    TaskStatus.READY,
    TaskStatus.INITIATED,
    TaskStatus.REQUESTING_RESOURCES,
    TaskStatus.RUNNING,
    TaskStatus.FINISHING,
}


def reopen_experiment_from_checkpoint(
    exp_id: ObjectId,
    *,
    task_id: ObjectId,
    resume_from: str | None = None,
    sample_positions: dict[str, str | None] | None = None,
    arm_home_confirmed: bool = False,
    continue_downstream: bool = True,
) -> dict[str, Any]:
    """Reopen ``task_id`` on experiment ``exp_id`` so TaskManager can run it again.

    Args:
        exp_id: Experiment ObjectId.
        task_id: Task to re-queue (typically the failed sub-task).
        resume_from: Optional phase name stored into task parameters (leaf modular_phase).
        sample_positions: Map of sample name → position to apply before resume.
        arm_home_confirmed: Required True; server does not jog the arm.
        continue_downstream: If True, restore cascade-cancelled next_tasks to WAITING.
    """
    if not arm_home_confirmed:
        raise ValueError(
            "Confirm the arm is at home / path is clear (arm_home_confirmed=true)."
        )

    experiment_view = ExperimentView()
    task_view = TaskView()
    sample_view = SampleView()

    experiment = _ensure_live_experiment(experiment_view, exp_id)
    task = task_view.get_task(task_id, encode=False)
    if task is None:
        raise ValueError(f"Task {task_id} not found.")

    task_exp = task.get("experiment_id") or task.get("exp_id")
    # Some deployments store experiment id only on the experiment.tasks list
    exp_task_ids: set[ObjectId] = set()
    for t in experiment.get("tasks") or []:
        if isinstance(t, ObjectId):
            exp_task_ids.add(t)
        elif isinstance(t, str):
            exp_task_ids.add(ObjectId(t))
        elif isinstance(t, dict) and t.get("task_id") is not None:
            exp_task_ids.add(ObjectId(t["task_id"]))
    # Also accept tasks listed inside experiment samples graph
    if task_id not in exp_task_ids and str(task_id) not in {
        str(x) for x in exp_task_ids
    }:
        # Fall back: allow if task samples belong to this experiment's samples
        exp_sample_ids = {
            ObjectId(s) if not isinstance(s, ObjectId) else s
            for s in (experiment.get("samples") or [])
            if isinstance(s, (ObjectId, str))
        }
        # experiment.samples may be dicts
        for s in experiment.get("samples") or []:
            if isinstance(s, dict) and s.get("sample_id"):
                exp_sample_ids.add(ObjectId(s["sample_id"]))
        task_sample_ids = []
        for s in task.get("samples") or []:
            if isinstance(s, dict) and s.get("sample_id"):
                task_sample_ids.append(ObjectId(s["sample_id"]))
            elif isinstance(s, ObjectId):
                task_sample_ids.append(s)
        if not task_sample_ids or not any(sid in exp_sample_ids for sid in task_sample_ids):
            # Still allow if experiment_id matches when present
            if task_exp and ObjectId(task_exp) != ObjectId(exp_id):
                raise ValueError("Task does not belong to this experiment.")

    status = TaskStatus[task["status"]] if isinstance(task["status"], str) else task["status"]
    if status in _LIVE_TASK:
        raise ValueError(
            f"Task is still {status.name}; cancel or wait for it to finish before resume."
        )
    if status not in _TERMINAL_TASK:
        raise ValueError(f"Cannot resume task in status {status}.")

    # Abort stray worker fields
    _clear_worker_fields(task_view, task_id, task)

    # Apply operator-confirmed positions
    applied_positions: dict[str, str | None] = {}
    if sample_positions:
        for sample_name, position in sample_positions.items():
            sample_id = _resolve_sample_id(sample_view, sample_name)
            sample_view.move_sample(sample_id=sample_id, position=position)
            applied_positions[sample_name] = position

    # Merge resume_from into parameters
    params = dict(task.get("parameters") or {})
    if resume_from:
        params["modular_phase"] = resume_from
        params["resume_from"] = resume_from
    task_view._task_collection.update_one(  # noqa: SLF001
        {"_id": ObjectId(task_id)},
        {
            "$set": {
                "parameters": params,
                "message": f"Reopened for resume at {datetime.now().isoformat(timespec='seconds')}",
                "reopened_at": datetime.now(),
            },
            "$unset": {
                "canceling_progress": "",
                "task_actor_id": "",
                "completed_at": "",
            },
        },
    )

    force_update_status(task_view, task_id, TaskStatus.READY)

    restored_downstream = 0
    if continue_downstream:
        restored_downstream = _restore_downstream(task_view, task)

    # Experiment back to RUNNING
    experiment_view._experiment_collection.update_one(  # noqa: SLF001
        {"_id": ObjectId(exp_id)},
        {
            "$set": {"status": ExperimentStatus.RUNNING.name},
            "$unset": {"completed_at": ""},
        },
    )

    return {
        "experiment_id": str(exp_id),
        "task_id": str(task_id),
        "task_status": TaskStatus.READY.name,
        "applied_positions": applied_positions,
        "downstream_restored": restored_downstream,
        "resume_from": resume_from,
    }


def force_update_status(
    task_view: TaskView, task_id: ObjectId, status: TaskStatus
) -> None:
    """Bypass sticky CANCELLED guard — reopen API only."""
    task_view._task_collection.update_one(  # noqa: SLF001
        {"_id": ObjectId(task_id)},
        {
            "$set": {
                "status": status.name,
                "result": None,
            }
        },
    )


def _clear_worker_fields(task_view: TaskView, task_id: ObjectId, task: dict) -> None:
    if task.get("canceling_progress") or task.get("task_actor_id"):
        try:
            from alab_management.lab_reset import _abort_task_actor

            _abort_task_actor(task)
        except Exception:
            logger.exception("Failed to abort task actor for %s", task_id)
        task_view._task_collection.update_one(  # noqa: SLF001
            {"_id": ObjectId(task_id)},
            {"$unset": {"canceling_progress": "", "task_actor_id": ""}},
        )


def _restore_downstream(task_view: TaskView, task: dict) -> int:
    """Set CANCELLED next_tasks that only depended on this task back to WAITING."""
    restored = 0
    for next_id in task.get("next_tasks") or []:
        next_id = ObjectId(next_id)
        next_task = task_view.get_task(next_id, encode=False)
        if not next_task:
            continue
        st = next_task["status"]
        if isinstance(st, str):
            st = TaskStatus[st]
        if st is not TaskStatus.CANCELLED:
            continue
        # Prefer cascade snapshot if present
        snapshot = (task.get("cascade_snapshot") or {}).get(str(next_id))
        if snapshot:
            task_view._task_collection.update_one(  # noqa: SLF001
                {"_id": next_id},
                {
                    "$set": {
                        "status": TaskStatus.WAITING.name,
                        "prev_tasks": snapshot.get(
                            "prev_tasks", next_task.get("prev_tasks")
                        ),
                        "samples": snapshot.get("samples", next_task.get("samples")),
                    },
                    "$unset": {"completed_at": "", "canceling_progress": ""},
                },
            )
        else:
            force_update_status(task_view, next_id, TaskStatus.WAITING)
            task_view._task_collection.update_one(  # noqa: SLF001
                {"_id": next_id},
                {"$unset": {"completed_at": "", "canceling_progress": ""}},
            )
        restored += 1
        try:
            task_view.try_to_mark_task_ready(task_id=next_id)
        except Exception:
            logger.debug("try_to_mark_task_ready failed for %s", next_id, exc_info=True)
    return restored


def _ensure_live_experiment(
    experiment_view: ExperimentView, exp_id: ObjectId
) -> dict[str, Any]:
    try:
        experiment = experiment_view.get_experiment(exp_id)
    except Exception:
        experiment = None
    if experiment:
        return experiment

    # Restore from completed DB if configured
    try:
        from alab_management.experiment_view.completed_experiment_view import (
            CompletedExperimentView,
        )

        completed = CompletedExperimentView()
        doc = completed.get_experiment(exp_id)
        if not doc:
            raise ValueError(f"Experiment {exp_id} not found in live or completed DB.")
        # Insert live copies of experiment / tasks / samples
        live_exp = get_collection("experiment")
        live_tasks = get_collection("tasks")
        live_samples = get_collection("samples")
        if live_exp.find_one({"_id": exp_id}) is None:
            live_exp.insert_one(doc)
        # tasks / samples may be nested — best-effort copy by id lists
        for tid in doc.get("tasks") or []:
            tid = ObjectId(tid) if not isinstance(tid, ObjectId) else tid
            if live_tasks.find_one({"_id": tid}) is None:
                try:
                    from alab_management.task_view.completed_task_view import (
                        CompletedTaskView,
                    )

                    tdoc = CompletedTaskView().get_task(tid, encode=False)
                    if tdoc:
                        live_tasks.insert_one(tdoc)
                except Exception:
                    logger.exception("Could not restore task %s", tid)
        for sid in doc.get("samples") or []:
            if isinstance(sid, dict):
                sid = sid.get("sample_id") or sid.get("_id")
            if not sid:
                continue
            sid = ObjectId(sid) if not isinstance(sid, ObjectId) else sid
            if live_samples.find_one({"_id": sid}) is None:
                try:
                    from alab_management.sample_view.completed_sample_view import (
                        CompletedSampleView,
                    )

                    sdoc = CompletedSampleView().get_sample(sid)
                    if sdoc:
                        live_samples.insert_one(
                            sdoc if isinstance(sdoc, dict) else sdoc.__dict__
                        )
                except Exception:
                    logger.exception("Could not restore sample %s", sid)
        return experiment_view.get_experiment(exp_id)
    except ValueError:
        raise
    except Exception as exc:
        raise ValueError(
            f"Experiment {exp_id} missing from live DB and could not restore: {exc}"
        ) from exc


def _resolve_sample_id(sample_view: SampleView, name_or_id: str) -> ObjectId:
    try:
        return ObjectId(name_or_id)
    except Exception:
        pass
    doc = sample_view._sample_collection.find_one({"name": name_or_id})  # noqa: SLF001
    if doc is None:
        raise ValueError(f"Cannot find sample {name_or_id!r}")
    return doc["_id"]


def record_cascade_snapshot(task_view: TaskView, task_id: ObjectId) -> None:
    """Store downstream prev_tasks/samples before cascade cancel (call from update_status)."""
    task = task_view.get_task(task_id, encode=False)
    if not task:
        return
    snap: dict[str, Any] = {}
    for next_id in task.get("next_tasks") or []:
        next_id = ObjectId(next_id)
        nxt = task_view.get_task(next_id, encode=False)
        if not nxt:
            continue
        snap[str(next_id)] = {
            "prev_tasks": list(nxt.get("prev_tasks") or []),
            "samples": list(nxt.get("samples") or []),
            "status": nxt.get("status"),
        }
    if snap:
        task_view._task_collection.update_one(  # noqa: SLF001
            {"_id": ObjectId(task_id)},
            {"$set": {"cascade_snapshot": snap}},
        )
