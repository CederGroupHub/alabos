"""Builtin Sample Summary generator."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from alab_management.dashboard.report_db import find_union

COLUMNS = [
    {"key": "sample_id", "label": "Sample ID"},
    {"key": "name", "label": "Name"},
    {"key": "position", "label": "Position"},
    {"key": "last_position", "label": "Last Position"},
    {"key": "metadata_keys", "label": "Metadata Keys"},
]


def run(*, start: datetime, end: datetime, live_db: Any, completed_db: Any) -> dict:
    date_filter = {"created_at": {"$gte": start, "$lt": end}}
    rows = []
    samples = find_union(
        "samples", date_filter, live_db=live_db, completed_db=completed_db
    )
    samples.sort(key=lambda s: s.get("created_at") or datetime.min)
    for sample in samples:
        rows.append(
            {
                "sample_id": str(sample["_id"]),
                "name": sample.get("name"),
                "position": sample.get("position"),
                "last_position": sample.get("last_position"),
                "task_id": str(sample["task_id"]) if sample.get("task_id") else None,
                "created_at": sample.get("created_at"),
                "last_updated": sample.get("last_updated"),
                "metadata_keys": ", ".join(
                    sorted((sample.get("metadata") or {}).keys())
                ),
                "tags": sample.get("tags", []),
            }
        )
    return {"columns": COLUMNS, "rows": rows}
