"""Five most recently created samples in the selected date range."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from alab_management.dashboard.report_db import find_union

COLUMNS = [
    {"key": "sample_id", "label": "Sample ID"},
    {"key": "name", "label": "Name"},
    {"key": "created_at", "label": "Created"},
    {"key": "position", "label": "Position"},
    {"key": "last_position", "label": "Last Position"},
    {"key": "metadata_keys", "label": "Metadata Keys"},
]

MAX_ROWS = 5


def run(*, start: datetime, end: datetime, live_db: Any, completed_db: Any) -> dict:
    date_filter = {"created_at": {"$gte": start, "$lt": end}}
    samples = find_union(
        "samples", date_filter, live_db=live_db, completed_db=completed_db
    )
    samples.sort(
        key=lambda s: s.get("created_at") or datetime.min,
        reverse=True,
    )
    rows = []
    for sample in samples[:MAX_ROWS]:
        rows.append(
            {
                "sample_id": str(sample["_id"]),
                "name": sample.get("name"),
                "created_at": sample.get("created_at"),
                "position": sample.get("position"),
                "last_position": sample.get("last_position"),
                "metadata_keys": ", ".join(
                    sorted((sample.get("metadata") or {}).keys())
                ),
            }
        )
    return {"columns": COLUMNS, "rows": rows}