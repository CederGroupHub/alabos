"""Builtin sample dosing & related-tasks report generator."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from bson import ObjectId
from bson.errors import InvalidId

from alab_management.dashboard.report_db import find_union
from alab_management.dashboard.sample_report import (
    build_sample_report_row,
    canonical_sample_name,
    enrich_groups_with_historical_dosing,
    same_name_mongo_filter,
    sample_has_dosing,
)

COLUMNS = [
    {"key": "name", "label": "Sample"},
    {"key": "aliases", "label": "Aliases"},
    {"key": "target_masses", "label": "Target mass"},
    {"key": "actual_masses", "label": "Actual mass"},
    {"key": "crucible", "label": "Crucible"},
    {"key": "mixing_pot", "label": "Mixing pot"},
    {"key": "heating_temperature", "label": "Heating T"},
    {"key": "dwell_hours", "label": "Dwell (h)"},
    {"key": "task_summary", "label": "Related tasks"},
]


def _as_object_id(value: Any) -> ObjectId | None:
    if value is None:
        return None
    if isinstance(value, ObjectId):
        return value
    try:
        return ObjectId(str(value))
    except (InvalidId, TypeError):
        return None


def _sample_id_str(sample_id: Any) -> str | None:
    return str(sample_id) if sample_id is not None else None


def _fetch_historical_dosing(
    names: list[str],
    *,
    exclude_ids: set[str],
    live_db: Any,
    completed_db: Any,
) -> list[dict[str, Any]]:
    if not names:
        return []
    clauses = [same_name_mongo_filter(name) for name in names]
    query: dict[str, Any] = {
        "$and": [
            {"$or": clauses} if len(clauses) > 1 else clauses[0],
            {"metadata.powderdosing_results": {"$exists": True}},
        ]
    }
    found: list[dict[str, Any]] = []
    for sample in find_union("samples", query, live_db=live_db, completed_db=completed_db):
        sid = str(sample["_id"]) if sample.get("_id") is not None else ""
        if sid and sid in exclude_ids:
            continue
        if sample_has_dosing(sample):
            found.append(sample)
    return found


def run(*, start: datetime, end: datetime, live_db: Any, completed_db: Any) -> dict:
    date_filter = {"created_at": {"$gte": start, "$lt": end}}
    samples_by_id: dict[str, dict[str, Any]] = {}
    for sample in find_union(
        "samples", date_filter, live_db=live_db, completed_db=completed_db
    ):
        samples_by_id[str(sample["_id"])] = sample

    extra_ids: list[ObjectId] = []
    for task in find_union(
        "tasks",
        date_filter,
        projection={"samples": 1},
        live_db=live_db,
        completed_db=completed_db,
    ):
        for sample in task.get("samples") or []:
            oid = _as_object_id(sample.get("sample_id"))
            if oid is not None and str(oid) not in samples_by_id:
                extra_ids.append(oid)
    if extra_ids:
        extra_ids = list(dict.fromkeys(extra_ids))
        for sample in find_union(
            "samples",
            {"_id": {"$in": extra_ids}},
            live_db=live_db,
            completed_db=completed_db,
        ):
            samples_by_id[str(sample["_id"])] = sample

    groups: dict[str, list[dict[str, Any]]] = {}
    for sample in samples_by_id.values():
        name = canonical_sample_name(sample.get("name"))
        if not name:
            continue
        groups.setdefault(name, []).append(sample)

    needs_dosing = [
        name
        for name, group in groups.items()
        if not any(sample_has_dosing(sample) for sample in group)
    ]
    if needs_dosing:
        historical = _fetch_historical_dosing(
            needs_dosing,
            exclude_ids=set(samples_by_id),
            live_db=live_db,
            completed_db=completed_db,
        )
        enrich_groups_with_historical_dosing(groups, historical)
        for sample in historical:
            sid = str(sample["_id"])
            if sid not in samples_by_id:
                samples_by_id[sid] = sample

    all_oids = [_as_object_id(sample["_id"]) for sample in samples_by_id.values()]
    all_oids = [oid for oid in all_oids if oid is not None]
    tasks_by_sid: dict[str, list[dict[str, Any]]] = {sid: [] for sid in samples_by_id}
    if all_oids:
        for task in find_union(
            "tasks",
            {"samples.sample_id": {"$in": all_oids}},
            live_db=live_db,
            completed_db=completed_db,
        ):
            for sample in task.get("samples") or []:
                sid = _sample_id_str(sample.get("sample_id"))
                if sid in tasks_by_sid:
                    tasks_by_sid[sid].append(task)

    rows = []
    for name in sorted(groups, key=lambda item: item.lower()):
        group = groups[name]
        related = []
        seen: set[str] = set()
        for sample in group:
            for task in tasks_by_sid.get(str(sample["_id"]), []):
                tid = str(task.get("_id"))
                if tid in seen:
                    continue
                seen.add(tid)
                related.append(task)
        row = build_sample_report_row(name, group, related)
        # Table cells: stringify list aliases for flat display.
        row["aliases"] = ", ".join(row.get("aliases") or [])
        rows.append(row)

    return {"columns": COLUMNS, "rows": rows}
