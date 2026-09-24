"""Builtin Task Outcome Log generator."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from bson import ObjectId

from alab_management.dashboard.report_db import find_union

COLUMNS = [
    {"key": "task_id", "label": "Task ID"},
    {"key": "type", "label": "Type"},
    {"key": "status", "label": "Status"},
    {"key": "sample_names", "label": "Samples"},
    {"key": "result_keys", "label": "Result Keys"},
]


def _task_result_keys(result: Any) -> list[str]:
    if isinstance(result, dict):
        return sorted(str(key) for key in result)
    if isinstance(result, ObjectId):
        return [f"gridfs:{result}"]
    if result is None:
        return []
    return [type(result).__name__]


def run(*, start: datetime, end: datetime, live_db: Any, completed_db: Any) -> dict:
    date_filter = {"created_at": {"$gte": start, "$lt": end}}
    tasks = find_union("tasks", date_filter, live_db=live_db, completed_db=completed_db)
    tasks.sort(key=lambda t: t.get("created_at") or datetime.min, reverse=True)
    rows = []
    for task in tasks:
        rows.append(
            {
                "task_id": str(task["_id"]),
                "type": task.get("type"),
                "status": task.get("status"),
                "created_at": task.get("created_at"),
                "started_at": task.get("started_at"),
                "completed_at": task.get("completed_at"),
                "last_updated": task.get("last_updated"),
                "message": task.get("message", ""),
                "sample_names": ", ".join(
                    str(sample.get("name") or "")
                    for sample in task.get("samples", [])
                    if sample.get("name")
                ),
                "sample_ids": [
                    str(sample.get("sample_id")) for sample in task.get("samples", [])
                ],
                "result_keys": ", ".join(_task_result_keys(task.get("result"))),
            }
        )
    return {"columns": COLUMNS, "rows": rows}
