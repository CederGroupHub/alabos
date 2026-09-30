"""Samples whose metadata.elements_present includes cobalt (Co)."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from alab_management.dashboard.report_db import find_union

COLUMNS = [
    {"key": "sample_id", "label": "Sample ID"},
    {"key": "name", "label": "Name"},
    {"key": "created_at", "label": "Created"},
    {"key": "target", "label": "Target composition"},
    {"key": "elements_present", "label": "Elements"},
]

MAX_ROWS = 5000
COBALT_SYMBOL = "Co"


def _elements_present(metadata: dict[str, Any]) -> list[str]:
    raw = metadata.get("elements_present") or []
    if not isinstance(raw, list):
        return []
    return [str(item) for item in raw if item is not None]


def sample_contains_cobalt(sample: dict[str, Any]) -> bool:
    return COBALT_SYMBOL in _elements_present(sample.get("metadata") or {})


def _cobalt_query(*, start: datetime, end: datetime) -> dict[str, Any]:
    return {
        "created_at": {"$gte": start, "$lt": end},
        "metadata.elements_present": COBALT_SYMBOL,
    }


def run(*, start: datetime, end: datetime, live_db: Any, completed_db: Any) -> dict:
    samples = find_union(
        "samples",
        _cobalt_query(start=start, end=end),
        live_db=live_db,
        completed_db=completed_db,
    )
    samples = [sample for sample in samples if sample_contains_cobalt(sample)]
    samples.sort(key=lambda s: s.get("created_at") or datetime.min)

    rows: list[dict[str, Any]] = []
    for sample in samples[:MAX_ROWS]:
        metadata = sample.get("metadata") or {}
        elements = _elements_present(metadata)
        rows.append(
            {
                "sample_id": str(sample["_id"]),
                "name": sample.get("name"),
                "created_at": sample.get("created_at"),
                "target": metadata.get("target"),
                "elements_present": ", ".join(elements),
            }
        )
    return {"columns": COLUMNS, "rows": rows}
