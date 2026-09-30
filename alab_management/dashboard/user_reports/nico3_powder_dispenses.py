"""Powder dispense target vs actual for samples that use NiCO3 (nickel carbonate)."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from bson import ObjectId
from bson.errors import InvalidId

from alab_management.dashboard.report_db import find_union

COLUMNS = [
    {"key": "sample_name", "label": "Sample"},
    {"key": "powder_name", "label": "Powder"},
    {"key": "target_mass", "label": "Target Mass"},
    {"key": "dose_mass", "label": "Actual Dose Mass"},
    {"key": "dose_head_position", "label": "Head Position"},
    {"key": "dose_timestamp", "label": "Dose Timestamp"},
]

MAX_ROWS = 5000


def _is_nico3_powder_name(name: Any) -> bool:
    text = str(name or "").strip()
    if not text:
        return False
    lowered = text.casefold()
    if lowered == "nico3":
        return True
    return "nickel carbonate" in lowered


def _precursors_dict(metadata: dict[str, Any]) -> dict[str, Any]:
    raw = metadata.get("precursors")
    return raw if isinstance(raw, dict) else {}


def _dosing_result_uses_nico3(dosing: dict[str, Any]) -> bool:
    for powder in dosing.get("Powders") or []:
        if _is_nico3_powder_name(powder.get("PowderName")):
            return True
    return False


def _name_tokens_suggest_nico3(name: Any) -> bool:
    text = str(name or "").strip()
    if not text:
        return False
    return any(_is_nico3_powder_name(part) for part in text.split("_"))


def sample_uses_nico3(sample: dict[str, Any]) -> bool:
    if _name_tokens_suggest_nico3(sample.get("name")):
        return True
    metadata = sample.get("metadata") or {}
    for key in _precursors_dict(metadata):
        if _is_nico3_powder_name(key):
            return True
    dosing = metadata.get("powderdosing_results") or {}
    for powder in dosing.get("Powders") or []:
        if _is_nico3_powder_name(powder.get("PowderName")):
            return True
    return False


def _sample_qualifies(
    *,
    sample_doc: dict[str, Any] | None,
    sample_name: str,
    dosing: dict[str, Any],
) -> bool:
    if _dosing_result_uses_nico3(dosing):
        return True
    if sample_doc and sample_uses_nico3(sample_doc):
        return True
    return _name_tokens_suggest_nico3(sample_name)


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


def _task_result_dict(result: Any) -> dict[str, Any]:
    return result if isinstance(result, dict) else {}


def _rows_for_sample_dosing(
    sample: dict[str, Any], dosing: dict[str, Any]
) -> list[dict[str, Any]]:
    display_name = sample.get("name") or ""
    sample_id = str(sample["_id"]) if sample.get("_id") is not None else None
    rows: list[dict[str, Any]] = []
    powders = dosing.get("Powders") or []
    if not powders:
        rows.append(
            {
                "sample_id": sample_id,
                "sample_name": display_name,
                "powder_name": None,
                "target_mass": None,
                "dose_mass": None,
                "dose_head_position": None,
                "dose_timestamp": None,
            }
        )
        return rows
    for powder in powders:
        doses = powder.get("Doses") or [None]
        for dose in doses:
            rows.append(
                {
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
    return rows


def _append_task_rows(
    rows: list[dict[str, Any]],
    *,
    task: dict[str, Any],
    sample_docs: dict[str, dict[str, Any]],
) -> None:
    sample_lookup: dict[str, dict[str, Any]] = {}
    for sample in task.get("samples") or []:
        task_name = sample.get("name")
        sample_id = _sample_id_str(sample.get("sample_id"))
        if not task_name:
            continue
        sample_lookup[task_name] = {
            "sample_id": sample_id,
            "sample_doc": sample_docs.get(sample_id) if sample_id else None,
        }

    results_per_sample = (
        _task_result_dict(task.get("result")).get("results_per_sample") or {}
    )
    for sample_name, dosing in results_per_sample.items():
        if not isinstance(dosing, dict):
            continue
        task_sample = sample_lookup.get(sample_name, {})
        sample_doc = task_sample.get("sample_doc")
        if not _sample_qualifies(
            sample_doc=sample_doc, sample_name=sample_name, dosing=dosing
        ):
            continue
        display_name = (
            sample_doc.get("name", sample_name) if sample_doc else sample_name
        )
        sample_id = task_sample.get("sample_id")
        pseudo_sample = {"name": display_name, "_id": sample_id}
        rows.extend(_rows_for_sample_dosing(pseudo_sample, dosing))


def run(*, start: datetime, end: datetime, live_db: Any, completed_db: Any) -> dict:
    date_filter = {"created_at": {"$gte": start, "$lt": end}}
    rows: list[dict[str, Any]] = []
    covered_sample_ids: set[str] = set()

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
        for sample in task.get("samples") or []:
            oid = _as_object_id(sample.get("sample_id"))
            if oid is not None:
                sample_object_ids.append(oid)
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

    for task in dosing_tasks:
        before = len(rows)
        _append_task_rows(rows, task=task, sample_docs=sample_docs)
        if len(rows) > before:
            for sample in task.get("samples") or []:
                sid = _sample_id_str(sample.get("sample_id"))
                if sid:
                    covered_sample_ids.add(sid)
        if len(rows) >= MAX_ROWS:
            return {"columns": COLUMNS, "rows": rows[:MAX_ROWS]}

    extra_sample_ids: list[ObjectId] = []
    for sample in find_union(
        "samples", date_filter, live_db=live_db, completed_db=completed_db
    ):
        sid = str(sample["_id"]) if sample.get("_id") is not None else ""
        if sid and sid in covered_sample_ids:
            continue
        if not sample_uses_nico3(sample):
            continue
        oid = _as_object_id(sample.get("_id"))
        if oid is not None:
            extra_sample_ids.append(oid)

    if extra_sample_ids:
        extra_sample_ids = list(dict.fromkeys(extra_sample_ids))
        for task in find_union(
            "tasks",
            {
                "type": "PowderDosing",
                "samples.sample_id": {"$in": extra_sample_ids},
            },
            live_db=live_db,
            completed_db=completed_db,
        ):
            task_sample_ids = {
                sid
                for sample in task.get("samples") or []
                if (sid := _sample_id_str(sample.get("sample_id")))
            }
            if not task_sample_ids.intersection(
                {str(oid) for oid in extra_sample_ids}
            ):
                continue
            docs = {
                str(sample["_id"]): sample
                for sample in find_union(
                    "samples",
                    {"_id": {"$in": extra_sample_ids}},
                    live_db=live_db,
                    completed_db=completed_db,
                )
            }
            _append_task_rows(rows, task=task, sample_docs={**sample_docs, **docs})
            if len(rows) >= MAX_ROWS:
                break

        for sample in find_union(
            "samples",
            {"_id": {"$in": extra_sample_ids}},
            live_db=live_db,
            completed_db=completed_db,
        ):
            sid = str(sample["_id"]) if sample.get("_id") is not None else ""
            if sid and sid in covered_sample_ids:
                continue
            metadata = sample.get("metadata") or {}
            dosing = metadata.get("powderdosing_results") or {}
            if dosing.get("Powders") or dosing.get("CruciblePosition"):
                rows.extend(_rows_for_sample_dosing(sample, dosing))
                if sid:
                    covered_sample_ids.add(sid)
            if len(rows) >= MAX_ROWS:
                break

    return {"columns": COLUMNS, "rows": rows[:MAX_ROWS]}
