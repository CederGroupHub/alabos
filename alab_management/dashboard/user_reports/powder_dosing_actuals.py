"""Builtin Powder Dosing Actuals generator."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from bson import ObjectId

from alab_management.dashboard.report_db import find_union

COLUMNS = [
    {"key": "sample_name", "label": "Sample"},
    {"key": "powder_name", "label": "Powder"},
    {"key": "target_mass", "label": "Target Mass"},
    {"key": "dose_mass", "label": "Actual Dose Mass"},
    {"key": "dose_head_position", "label": "Head Position"},
    {"key": "dose_timestamp", "label": "Dose Timestamp"},
]


def _sample_id_str(sample_id: Any) -> str | None:
    return str(sample_id) if sample_id is not None else None


def _task_result_dict(result: Any) -> dict[str, Any]:
    return result if isinstance(result, dict) else {}


def run(*, start: datetime, end: datetime, live_db: Any, completed_db: Any) -> dict:
    date_filter = {"created_at": {"$gte": start, "$lt": end}}
    dosing_tasks = list(
        find_union(
            "tasks",
            {"type": "PowderDosing", **date_filter},
            live_db=live_db,
            completed_db=completed_db,
        )
    )
    dosing_tasks.sort(key=lambda t: t.get("created_at") or datetime.min)

    sample_object_ids: list[ObjectId] = []
    for task in dosing_tasks:
        for sample in task.get("samples", []):
            sample_id = sample.get("sample_id")
            if sample_id is not None:
                sample_object_ids.append(ObjectId(sample_id))
    sample_object_ids = list(dict.fromkeys(sample_object_ids))

    sample_docs: dict[str, dict[str, Any]] = {}
    if sample_object_ids:
        sample_docs = {
            str(sample["_id"]): sample
            for sample in find_union(
                "samples",
                {"_id": {"$in": sample_object_ids}},
                live_db=live_db,
                completed_db=completed_db,
            )
        }

    rows: list[dict[str, Any]] = []
    for task in dosing_tasks:
        sample_lookup = {}
        for sample in task.get("samples", []):
            sample_name = sample.get("name")
            sample_id = _sample_id_str(sample.get("sample_id"))
            if sample_name:
                sample_lookup[sample_name] = {
                    "sample_id": sample_id,
                    "sample_doc": sample_docs.get(sample_id) if sample_id else None,
                }
        results_per_sample = (
            _task_result_dict(task.get("result")).get("results_per_sample") or {}
        )
        for sample_name, dosing in results_per_sample.items():
            task_sample = sample_lookup.get(sample_name, {})
            sample_id = task_sample.get("sample_id")
            sample_doc = task_sample.get("sample_doc")
            display_name = (
                sample_doc.get("name", sample_name) if sample_doc else sample_name
            )
            powders = dosing.get("Powders") or []
            if not powders:
                rows.append(
                    {
                        "task_id": str(task["_id"]),
                        "sample_id": sample_id,
                        "sample_name": display_name,
                        "powder_name": None,
                        "target_mass": None,
                        "dose_mass": None,
                        "dose_head_position": None,
                        "dose_timestamp": None,
                    }
                )
                continue
            for powder in powders:
                doses = powder.get("Doses") or [None]
                for dose in doses:
                    rows.append(
                        {
                            "task_id": str(task["_id"]),
                            "sample_id": sample_id,
                            "sample_name": display_name,
                            "powder_name": powder.get("PowderName"),
                            "target_mass": powder.get("TargetMass"),
                            "dose_mass": None if dose is None else dose.get("Mass"),
                            "dose_head_position": None
                            if dose is None
                            else dose.get("HeadPosition"),
                            "dose_timestamp": None
                            if dose is None
                            else dose.get("TimeStamp"),
                        }
                    )
    return {"columns": COLUMNS, "rows": rows}
