"""Derive previous / current / next task summaries for the Experiments dashboard."""

from __future__ import annotations

import re
from datetime import datetime
from typing import Any

from bson import ObjectId

from alab_management.task_view.task_enums import TaskStatus

LIVE_STATUSES = frozenset(
    {
        TaskStatus.INITIATED.name,
        TaskStatus.REQUESTING_RESOURCES.name,
        TaskStatus.RUNNING.name,
        TaskStatus.FINISHING.name,
    }
)

TERMINAL_STATUSES = frozenset(
    {
        TaskStatus.COMPLETED.name,
        TaskStatus.ERROR.name,
        TaskStatus.CANCELLED.name,
    }
)


def humanize_task_type(task_type: str) -> str:
    """Turn ``RecoverPowder`` into ``Recover powder``."""
    text = (task_type or "").strip() or "Task"
    spaced = re.sub(r"(?<!^)([A-Z])", r" \1", text).replace("_", " ")
    parts = spaced.split()
    if not parts:
        return "Task"
    return parts[0] + (" " + " ".join(p.lower() for p in parts[1:]) if len(parts) > 1 else "")


def sample_names_from_task(task: dict[str, Any]) -> list[str]:
    names: list[str] = []
    for sample in task.get("samples") or []:
        if isinstance(sample, dict):
            name = sample.get("name")
            if name:
                names.append(str(name))
        elif sample:
            names.append(str(sample))
    return names


def build_task_description(task: dict[str, Any]) -> str:
    """Operator-facing one-liner from type, samples, and live message."""
    parts = [humanize_task_type(str(task.get("type") or "Task"))]
    samples = sample_names_from_task(task)
    if samples:
        parts.append(", ".join(samples))
    message = (task.get("message") or "").strip()
    if message:
        parts.append(message)
    return " — ".join(parts)


def _as_object_id(value: Any) -> ObjectId | None:
    if value is None:
        return None
    if isinstance(value, ObjectId):
        return value
    try:
        return ObjectId(str(value))
    except Exception:
        return None


def _status_name(value: Any) -> str:
    if isinstance(value, TaskStatus):
        return value.name
    return str(value or "")


def _parse_time(value: Any) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value)
        except ValueError:
            return None
    return None


def summarize_task(task: dict[str, Any]) -> dict[str, Any]:
    """JSON-friendly task summary for progress_steps / enriched tasks list."""
    task_id = task.get("_id") or task.get("id")
    summary: dict[str, Any] = {
        "id": str(task_id) if task_id is not None else "",
        "type": task.get("type") or "",
        "status": _status_name(task.get("status")),
        "description": build_task_description(task),
        "message": task.get("message") or "",
        "samples": sample_names_from_task(task),
    }
    if task.get("started_at") is not None:
        summary["started_at"] = task.get("started_at")
    if task.get("completed_at") is not None:
        summary["completed_at"] = task.get("completed_at")
    return summary


def _prev_ids(task: dict[str, Any]) -> set[ObjectId]:
    ids: set[ObjectId] = set()
    for raw in task.get("prev_tasks") or []:
        oid = _as_object_id(raw)
        if oid is not None:
            ids.add(oid)
    return ids


def _task_id(task: dict[str, Any]) -> ObjectId | None:
    return _as_object_id(task.get("_id") or task.get("id"))


def compute_progress_steps(tasks: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    """Classify experiment tasks into previous / current / next summaries.

    * **current** — live statuses (initiated through finishing)
    * **previous** — direct completed predecessors of current tasks when available;
      otherwise the latest ``COMPLETED`` task by ``completed_at``
    * **next** — ``READY``, or ``WAITING`` whose every prev task is ``COMPLETED``
    """
    by_id: dict[ObjectId, dict[str, Any]] = {}
    for task in tasks:
        oid = _task_id(task)
        if oid is not None:
            by_id[oid] = task

    current_tasks = [
        task
        for task in tasks
        if _status_name(task.get("status")) in LIVE_STATUSES
    ]

    previous_tasks: list[dict[str, Any]] = []
    if current_tasks:
        feeder_ids: set[ObjectId] = set()
        for task in current_tasks:
            feeder_ids |= _prev_ids(task)
        feeders = [
            by_id[oid]
            for oid in feeder_ids
            if oid in by_id
            and _status_name(by_id[oid].get("status")) == TaskStatus.COMPLETED.name
        ]
        if feeders:
            previous_tasks = feeders
        else:
            completed = [
                task
                for task in tasks
                if _status_name(task.get("status")) == TaskStatus.COMPLETED.name
            ]
            if completed:
                previous_tasks = [
                    max(
                        completed,
                        key=lambda t: _parse_time(t.get("completed_at"))
                        or datetime.min,
                    )
                ]
    else:
        completed = [
            task
            for task in tasks
            if _status_name(task.get("status")) == TaskStatus.COMPLETED.name
        ]
        if completed:
            previous_tasks = [
                max(
                    completed,
                    key=lambda t: _parse_time(t.get("completed_at")) or datetime.min,
                )
            ]

    next_tasks: list[dict[str, Any]] = []
    for task in tasks:
        status = _status_name(task.get("status"))
        if status == TaskStatus.READY.name:
            next_tasks.append(task)
            continue
        if status != TaskStatus.WAITING.name:
            continue
        prevs = _prev_ids(task)
        if not prevs:
            # No predecessors and still WAITING — treat as next if nothing is blocking.
            next_tasks.append(task)
            continue
        if all(
            oid in by_id
            and _status_name(by_id[oid].get("status")) == TaskStatus.COMPLETED.name
            for oid in prevs
        ):
            next_tasks.append(task)

    # Stable order: preserve experiment task list order.
    order = {_task_id(t): i for i, t in enumerate(tasks) if _task_id(t) is not None}

    def _sort_key(task: dict[str, Any]) -> int:
        oid = _task_id(task)
        return order.get(oid, 10**9) if oid is not None else 10**9

    return {
        "previous": [summarize_task(t) for t in sorted(previous_tasks, key=_sort_key)],
        "current": [summarize_task(t) for t in sorted(current_tasks, key=_sort_key)],
        "next": [summarize_task(t) for t in sorted(next_tasks, key=_sort_key)],
    }
