"""Curated data export routes for the dashboard."""

from __future__ import annotations

import csv
import io
from calendar import monthrange
from datetime import datetime, timedelta
from typing import Any

from bson import ObjectId
from bson.errors import InvalidId
from flask import Blueprint, Response, jsonify, request

from alab_management.dashboard.lab_views import sample_view, task_view
from alab_management.dashboard.sample_report import (
    build_sample_report_row,
    canonical_sample_name,
    enrich_groups_with_historical_dosing,
    same_name_mongo_filter,
    sample_has_dosing,
)
from alab_management.utils.data_objects import (
    get_completed_collection,
    make_jsonable,
)

data_bp = Blueprint("/data", __name__, url_prefix="/api/data")


def _get_history_collection(name: str):
    """Prefer the completed DB for historical exports, falling back to the working DB."""
    try:
        completed = get_completed_collection(name)
        if completed.find_one({}, projection={"_id": 1}) is not None:
            return completed
    except ValueError:
        pass

    if name == "samples":
        return sample_view._sample_collection
    if name == "tasks":
        return task_view._task_collection
    raise ValueError(f"Unsupported history collection: {name}")


def _month_window(month_key: str) -> tuple[datetime, datetime]:
    year, month = (int(part) for part in month_key.split("-"))
    start = datetime(year, month, 1)
    if month == 12:
        end = datetime(year + 1, 1, 1)
    else:
        end = datetime(year, month + 1, 1)
    return start, end


def _default_month_key() -> str:
    now = datetime.now()
    return f"{now.year:04d}-{now.month:02d}"


def _parse_month_key(month_key: str | None) -> str:
    if not month_key:
        return _default_month_key()
    try:
        year, month = (int(part) for part in month_key.split("-"))
        if month < 1 or month > 12:
            raise ValueError
        monthrange(year, month)
    except (TypeError, ValueError):
        raise ValueError("month must be YYYY-MM") from None
    return f"{year:04d}-{month:02d}"


def _parse_calendar_date(value: str | None, *, field: str) -> datetime:
    raw = str(value or "").strip()
    try:
        return datetime.strptime(raw, "%Y-%m-%d")
    except (TypeError, ValueError):
        raise ValueError(f"{field} must be YYYY-MM-DD") from None


def _format_range_label(start: datetime, end_inclusive: datetime) -> str:
    if start.date() == end_inclusive.date():
        return start.strftime("%b %d, %Y")
    last_day = monthrange(start.year, start.month)[1]
    if (
        start.year == end_inclusive.year
        and start.month == end_inclusive.month
        and start.day == 1
        and end_inclusive.day == last_day
    ):
        return start.strftime("%B %Y")
    if start.year == end_inclusive.year and start.month == end_inclusive.month:
        return f"{start.strftime('%b')} {start.day}–{end_inclusive.day}, {start.year}"
    if start.year == end_inclusive.year:
        return (
            f"{start.strftime('%b')} {start.day} – "
            f"{end_inclusive.strftime('%b')} {end_inclusive.day}, {start.year}"
        )
    return f"{start.strftime('%b %d, %Y')} – {end_inclusive.strftime('%b %d, %Y')}"


def _month_key_if_full_month(start: datetime, end_exclusive: datetime) -> str | None:
    if start.day != 1:
        return None
    month_key = f"{start.year:04d}-{start.month:02d}"
    _, month_end = _month_window(month_key)
    return month_key if end_exclusive == month_end else None


def _range_metadata(start: datetime, end_exclusive: datetime) -> dict[str, Any]:
    """Build a query window. ``end_exclusive`` is the first instant *after* the range."""
    if end_exclusive <= start:
        raise ValueError("end must be on or after start")
    end_inclusive = end_exclusive - timedelta(days=1)
    month_key = _month_key_if_full_month(start, end_exclusive)
    tasks_col = _get_history_collection("tasks")
    has_older = (
        tasks_col.find_one({"created_at": {"$lt": start}}, projection={"_id": 1})
        is not None
    )
    current_month = _default_month_key()
    if month_key is not None:
        has_newer = month_key < current_month
    else:
        has_newer = (
            tasks_col.find_one(
                {"created_at": {"$gte": end_exclusive}}, projection={"_id": 1}
            )
            is not None
        )
    return {
        "month": month_key,
        "label": _format_range_label(start, end_inclusive),
        "start": start,
        "end": end_exclusive,
        "start_date": start.strftime("%Y-%m-%d"),
        "end_date": end_inclusive.strftime("%Y-%m-%d"),
        "has_older": has_older,
        "has_newer": has_newer,
    }


def _window_metadata(month_key: str) -> dict[str, Any]:
    start, end = _month_window(month_key)
    return _range_metadata(start, end)


def _window_from_params(
    *,
    month: str | None = None,
    start: str | None = None,
    end: str | None = None,
) -> dict[str, Any]:
    """Resolve month=YYYY-MM or start/end=YYYY-MM-DD (inclusive calendar days)."""
    if start is not None or end is not None:
        if not start or not end:
            raise ValueError("start and end are required together (YYYY-MM-DD)")
        start_dt = _parse_calendar_date(start, field="start")
        end_inclusive = _parse_calendar_date(end, field="end")
        if end_inclusive < start_dt:
            raise ValueError("end must be on or after start")
        return _range_metadata(start_dt, end_inclusive + timedelta(days=1))
    return _window_metadata(_parse_month_key(month))


def _window_from_request() -> dict[str, Any]:
    return _window_from_params(
        month=request.args.get("month"),
        start=request.args.get("start"),
        end=request.args.get("end"),
    )


def _created_at_filter(start: datetime, end: datetime) -> dict[str, Any]:
    return {"created_at": {"$gte": start, "$lt": end}}


def _nav_month_keys(window: dict[str, Any]) -> tuple[str | None, str | None]:
    """Previous/next calendar-month shortcuts relative to the active window."""
    anchor = window.get("month") or window["start"].strftime("%Y-%m")
    older = _shift_month(anchor, -1) if window.get("has_older") else None
    newer = _shift_month(anchor, 1) if window.get("has_newer") else None
    return older, newer


def _response_payload(rows: list[dict[str, Any]], window: dict[str, Any]) -> dict[str, Any]:
    return {
        "status": "success",
        "window": make_jsonable(
            {
                "month": window.get("month"),
                "label": window["label"],
                "start_date": window["start_date"],
                "end_date": window["end_date"],
                "has_older": window["has_older"],
                "has_newer": window["has_newer"],
            }
        ),
        "rows": make_jsonable(rows),
    }


def _sample_id_str(sample_id: Any) -> str | None:
    return str(sample_id) if sample_id is not None else None


def _sample_metadata(sample_doc: dict[str, Any] | None) -> dict[str, Any]:
    return (sample_doc or {}).get("metadata") or {}


def _find_first_task_of_type(tasks: list[dict[str, Any]], task_type: str) -> dict[str, Any] | None:
    for task in tasks:
        if task.get("type") == task_type:
            return task
    return None


def _sample_summary_rows(window: dict[str, Any]) -> list[dict[str, Any]]:
    rows = []
    date_filter = _created_at_filter(window["start"], window["end"])
    for sample in (
        _get_history_collection("samples")
        .find(date_filter)
        .sort("created_at", 1)
    ):
        rows.append(
            {
                "sample_id": str(sample["_id"]),
                "name": sample["name"],
                "position": sample.get("position"),
                "last_position": sample.get("last_position"),
                "task_id": str(sample["task_id"]) if sample.get("task_id") else None,
                "created_at": sample.get("created_at"),
                "last_updated": sample.get("last_updated"),
                "metadata_keys": sorted((sample.get("metadata") or {}).keys()),
                "tags": sample.get("tags", []),
            }
        )
    return rows


def _powder_dosing_rows(window: dict[str, Any]) -> list[dict[str, Any]]:
    rows = []
    date_filter = _created_at_filter(window["start"], window["end"])
    tasks_col = _get_history_collection("tasks")
    samples_col = _get_history_collection("samples")

    dosing_tasks = list(
        tasks_col.find({"type": "PowderDosing", **date_filter}).sort("created_at", 1)
    )

    sample_object_ids: list[ObjectId] = []
    for task in dosing_tasks:
        for sample in task.get("samples", []):
            sample_id = sample.get("sample_id")
            if sample_id is not None:
                sample_object_ids.append(ObjectId(sample_id))
    sample_object_ids = list(dict.fromkeys(sample_object_ids))

    sample_docs = {
        str(sample["_id"]): sample
        for sample in samples_col.find({"_id": {"$in": sample_object_ids}})
    }

    tasks_by_sample_id: dict[str, list[dict[str, Any]]] = {sid: [] for sid in sample_docs}
    if sample_object_ids:
        for task in tasks_col.find({"samples.sample_id": {"$in": sample_object_ids}}):
            for sample in task.get("samples", []):
                sample_id = _sample_id_str(sample.get("sample_id"))
                if sample_id in tasks_by_sample_id:
                    tasks_by_sample_id[sample_id].append(task)

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
        results_per_sample = _task_result_dict(task.get("result")).get("results_per_sample") or {}
        for sample_name, dosing in results_per_sample.items():
            task_sample = sample_lookup.get(sample_name, {})
            sample_id = task_sample.get("sample_id")
            sample_doc = task_sample.get("sample_doc")
            sample_metadata = _sample_metadata(sample_doc)
            related_tasks = tasks_by_sample_id.get(sample_id, []) if sample_id else []
            heating_task = _find_first_task_of_type(related_tasks, "Heating")
            heating_parameters = (heating_task or {}).get("parameters") or {}
            powder_input = (
                ((task.get("parameters") or {}).get("inputfiles") or {}).get(sample_name)
                or {}
            )
            powders = dosing.get("Powders") or []
            if not powders:
                rows.append(
                    {
                        "task_id": str(task["_id"]),
                        "task_status": task.get("status"),
                        "sample_id": sample_id,
                        "sample_name": sample_doc.get("name", sample_name)
                        if sample_doc
                        else sample_name,
                        "sample_target": sample_metadata.get("target"),
                        "elements_present": sample_metadata.get("elements_present"),
                        "mixing_pot_position": dosing.get("MixingPotPosition"),
                        "crucible_position": dosing.get("CruciblePosition"),
                        "crucible_subrack": dosing.get("CrucibleSubRack"),
                        "actual_transfer_mass": dosing.get("ActualTransferMass"),
                        "actual_heat_duration": dosing.get("ActualHeatDuration"),
                        "heating_duration": powder_input.get("HeatingDuration"),
                        "heating_time": heating_parameters.get("heating_time"),
                        "heating_temperature": heating_parameters.get("heating_temperature"),
                        "ramping_rate": heating_parameters.get("ramping_rate"),
                        "cooling_rate": heating_parameters.get("cooling_rate"),
                        "target_transfer_volume": dosing.get("TargetTransferVolume"),
                        "ethanol_dispense_volume": dosing.get("EthanolDispenseVolume"),
                        "transfer_time": dosing.get("TransferTime"),
                        "end_reason": dosing.get("EndReason"),
                        "powder_name": None,
                        "target_mass": None,
                        "actual_dispensed_mass_total": None,
                        "actual_minus_target_mass": None,
                        "dose_count": 0,
                        "dose_head_positions": [],
                        "dose_masses": [],
                        "dose_timestamps": [],
                        "dose_head_position": None,
                        "dose_mass": None,
                        "dose_timestamp": None,
                    }
                )
                continue

            for powder in powders:
                doses = powder.get("Doses") or [None]
                dose_masses = [dose.get("Mass") for dose in doses if dose is not None]
                total_actual_mass = sum(
                    mass for mass in dose_masses if isinstance(mass, (int, float))
                )
                target_mass = powder.get("TargetMass")
                for dose in doses:
                    rows.append(
                        {
                            "task_id": str(task["_id"]),
                            "task_status": task.get("status"),
                            "sample_id": sample_id,
                            "sample_name": sample_doc.get("name", sample_name)
                            if sample_doc
                            else sample_name,
                            "sample_target": sample_metadata.get("target"),
                            "elements_present": sample_metadata.get("elements_present"),
                            "mixing_pot_position": dosing.get("MixingPotPosition"),
                            "crucible_position": dosing.get("CruciblePosition"),
                            "crucible_subrack": dosing.get("CrucibleSubRack"),
                            "actual_transfer_mass": dosing.get("ActualTransferMass"),
                            "actual_heat_duration": dosing.get("ActualHeatDuration"),
                            "heating_duration": powder_input.get("HeatingDuration"),
                            "heating_time": heating_parameters.get("heating_time"),
                            "heating_temperature": heating_parameters.get("heating_temperature"),
                            "ramping_rate": heating_parameters.get("ramping_rate"),
                            "cooling_rate": heating_parameters.get("cooling_rate"),
                            "target_transfer_volume": dosing.get("TargetTransferVolume"),
                            "ethanol_dispense_volume": dosing.get("EthanolDispenseVolume"),
                            "transfer_time": dosing.get("TransferTime"),
                            "end_reason": dosing.get("EndReason"),
                            "powder_name": powder.get("PowderName"),
                            "target_mass": target_mass,
                            "actual_dispensed_mass_total": total_actual_mass,
                            "actual_minus_target_mass": None
                            if not isinstance(target_mass, (int, float))
                            else total_actual_mass - target_mass,
                            "dose_count": len(dose_masses),
                            "dose_head_positions": [
                                dose_entry.get("HeadPosition")
                                for dose_entry in doses
                                if dose_entry is not None
                            ],
                            "dose_masses": dose_masses,
                            "dose_timestamps": [
                                dose_entry.get("TimeStamp")
                                for dose_entry in doses
                                if dose_entry is not None
                            ],
                            "dose_head_position": None
                            if dose is None
                            else dose.get("HeadPosition"),
                            "dose_mass": None if dose is None else dose.get("Mass"),
                            "dose_timestamp": None if dose is None else dose.get("TimeStamp"),
                        }
                    )
    return rows


def _as_object_id(value: Any) -> ObjectId | None:
    if value is None:
        return None
    if isinstance(value, ObjectId):
        return value
    try:
        return ObjectId(str(value))
    except (InvalidId, TypeError):
        return None


def _fetch_historical_dosing_samples(
    samples_col: Any,
    names: list[str],
    *,
    exclude_ids: set[str],
) -> list[dict[str, Any]]:
    """Load archived same-name samples that still carry Labman dosing results."""
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
    for sample in samples_col.find(query):
        sid = str(sample["_id"]) if sample.get("_id") is not None else ""
        if sid and sid in exclude_ids:
            continue
        if sample_has_dosing(sample):
            found.append(sample)
    return found


def _sample_report_rows(window: dict[str, Any]) -> list[dict[str, Any]]:
    """One row per collapsed sample name, with dosing + every related task."""
    date_filter = _created_at_filter(window["start"], window["end"])
    samples_col = _get_history_collection("samples")
    tasks_col = _get_history_collection("tasks")

    samples_by_id: dict[str, dict[str, Any]] = {}
    for sample in samples_col.find(date_filter):
        samples_by_id[str(sample["_id"])] = sample

    extra_ids: list[ObjectId] = []
    for task in tasks_col.find(date_filter, projection={"samples": 1}):
        for sample in task.get("samples") or []:
            oid = _as_object_id(sample.get("sample_id"))
            if oid is not None and str(oid) not in samples_by_id:
                extra_ids.append(oid)
    if extra_ids:
        extra_ids = list(dict.fromkeys(extra_ids))
        for sample in samples_col.find({"_id": {"$in": extra_ids}}):
            samples_by_id[str(sample["_id"])] = sample

    groups: dict[str, list[dict[str, Any]]] = {}
    for sample in samples_by_id.values():
        name = canonical_sample_name(sample.get("name"))
        if not name:
            continue
        groups.setdefault(name, []).append(sample)

    # Re-runs in a later month create new sample IDs without powderdosing_results.
    # Pull older same-name docs that still carry Labman dosing so powders fill in.
    needs_dosing = [
        name
        for name, group in groups.items()
        if not any(sample_has_dosing(sample) for sample in group)
    ]
    if needs_dosing:
        historical = _fetch_historical_dosing_samples(
            samples_col,
            needs_dosing,
            exclude_ids=set(samples_by_id),
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
        for task in tasks_col.find({"samples.sample_id": {"$in": all_oids}}):
            for sample in task.get("samples") or []:
                sid = _sample_id_str(sample.get("sample_id"))
                if sid in tasks_by_sid:
                    tasks_by_sid[sid].append(task)

    rows = []
    for name in sorted(groups, key=lambda item: item.lower()):
        group = groups[name]
        related = []
        seen = set()
        for sample in group:
            for task in tasks_by_sid.get(str(sample["_id"]), []):
                tid = str(task.get("_id"))
                if tid in seen:
                    continue
                seen.add(tid)
                related.append(task)
        rows.append(build_sample_report_row(name, group, related))
    return rows


def _task_result_keys(result: Any) -> list[str]:
    if isinstance(result, dict):
        return sorted(str(key) for key in result.keys())
    if isinstance(result, ObjectId):
        return [f"gridfs:{result}"]
    if result is None:
        return []
    return [type(result).__name__]


def _task_result_dict(result: Any) -> dict[str, Any]:
    if isinstance(result, dict):
        return result
    return {}


def _task_outcome_rows(window: dict[str, Any]) -> list[dict[str, Any]]:
    rows = []
    date_filter = _created_at_filter(window["start"], window["end"])
    for task in (
        _get_history_collection("tasks")
        .find(date_filter)
        .sort("created_at", -1)
    ):
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
                "sample_names": [sample.get("name") for sample in task.get("samples", [])],
                "sample_ids": [str(sample.get("sample_id")) for sample in task.get("samples", [])],
                "result_keys": _task_result_keys(task.get("result")),
            }
        )
    return rows


def _csv_response(filename: str, rows: list[dict[str, Any]]) -> Response:
    output = io.StringIO()
    fieldnames = list(rows[0].keys()) if rows else []
    writer = csv.DictWriter(output, fieldnames=fieldnames)
    if fieldnames:
        writer.writeheader()
        for row in rows:
            writer.writerow(
                {
                    key: _csv_cell(value)
                    for key, value in row.items()
                }
            )
    response = Response(output.getvalue(), mimetype="text/csv")
    response.headers["Content-Disposition"] = f"attachment; filename={filename}"
    return response


def _csv_cell(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, (list, dict, tuple)):
        return str(make_jsonable(value))
    return str(value)


def _shift_month(month_key: str, delta: int) -> str:
    year, month = (int(part) for part in month_key.split("-"))
    month += delta
    while month < 1:
        month += 12
        year -= 1
    while month > 12:
        month -= 12
        year += 1
    return f"{year:04d}-{month:02d}"


@data_bp.route("/window", methods=["GET"])
def data_window():
    """Return the active date window and whether older/newer periods exist."""
    try:
        window = _window_from_request()
    except ValueError as exc:
        return jsonify({"status": "error", "errors": str(exc)}), 400
    older_month, newer_month = _nav_month_keys(window)
    return jsonify(
        {
            "status": "success",
            "window": make_jsonable(
                {
                    "month": window.get("month"),
                    "label": window["label"],
                    "start_date": window["start_date"],
                    "end_date": window["end_date"],
                    "has_older": window["has_older"],
                    "has_newer": window["has_newer"],
                    "older_month": older_month,
                    "newer_month": newer_month,
                }
            ),
        }
    )


@data_bp.route("/reports", methods=["GET"])
def list_data_reports():
    """List enabled Data report registry entries (no row payloads)."""
    from alab_management.dashboard import data_reports as reports

    try:
        reports.ensure_builtin_reports()
        items = reports.list_reports(enabled_only=True)
    except Exception as exc:
        return jsonify({"status": "error", "errors": str(exc)}), 400
    return jsonify({"status": "success", "reports": items})


@data_bp.route("/reports", methods=["POST"])
def create_data_report():
    """Register a report generator module (metadata only; does not execute code from body)."""
    from alab_management.dashboard import data_reports as reports

    data = request.get_json(silent=True) or {}
    try:
        reports.ensure_builtin_reports()
        doc = reports.upsert_report_metadata(
            data, created_by=str(data.get("created_by") or "api")
        )
    except Exception as exc:
        return jsonify({"status": "error", "errors": str(exc)}), 400
    return jsonify({"status": "success", "report": doc})


@data_bp.route("/reports/<name>", methods=["PATCH"])
def patch_data_report(name: str):
    """Rename / save-flag / enable a non-destructive metadata update."""
    from alab_management.dashboard import data_reports as reports

    data = request.get_json(silent=True) or {}
    try:
        doc = reports.patch_report(name, data)
    except Exception as exc:
        return jsonify({"status": "error", "errors": str(exc)}), 400
    return jsonify({"status": "success", "report": doc})


@data_bp.route("/reports/<name>", methods=["DELETE"])
def delete_data_report(name: str):
    """Delete a non-builtin report."""
    from alab_management.dashboard import data_reports as reports

    try:
        reports.delete_report(name)
    except Exception as exc:
        return jsonify({"status": "error", "errors": str(exc)}), 400
    return jsonify({"status": "success", "name": name})


@data_bp.route("/reports/<name>/rows", methods=["GET"])
def data_report_rows(name: str):
    """Return the stored snapshot for a report."""
    from alab_management.dashboard import data_reports as reports

    try:
        reports.ensure_builtin_reports()
        snap = reports.get_report_snapshot(name)
        if snap is None:
            raise ValueError(f"Unknown report '{name}'.")
    except Exception as exc:
        return jsonify({"status": "error", "errors": str(exc)}), 400
    return jsonify({"status": "success", "report": snap})


@data_bp.route("/reports/<name>/refresh", methods=["POST"])
def refresh_data_report(name: str):
    """Re-run the allowlisted generator and update the snapshot."""
    from alab_management.dashboard import data_reports as reports

    try:
        window = _window_from_request()
        reports.ensure_builtin_reports()
        snap = reports.refresh_report(
            name,
            start=window["start"],
            end=window["end"],
            start_date=window["start_date"],
            end_date=window["end_date"],
        )
    except Exception as exc:
        return jsonify({"status": "error", "errors": str(exc)}), 400
    return jsonify(
        {
            "status": "success",
            "report": snap,
            "window": make_jsonable(
                {
                    "label": window["label"],
                    "start_date": window["start_date"],
                    "end_date": window["end_date"],
                    "month": window.get("month"),
                }
            ),
        }
    )


@data_bp.route("/reports/<name>.csv", methods=["GET"])
def data_report_csv(name: str):
    """Download the current snapshot as CSV."""
    from alab_management.dashboard import data_reports as reports

    try:
        reports.ensure_builtin_reports()
        snap = reports.get_report_snapshot(name)
        if snap is None:
            raise ValueError(f"Unknown report '{name}'.")
    except Exception as exc:
        return jsonify({"status": "error", "errors": str(exc)}), 400
    columns = snap.get("columns") or []
    rows = snap.get("rows") or []
    if columns:
        flat_rows = []
        keys = [col["key"] for col in columns]
        for row in rows:
            flat_rows.append({key: row.get(key) for key in keys})
    else:
        flat_rows = rows
    return _csv_response(f"{name}.csv", flat_rows)


@data_bp.route("/report_jobs", methods=["POST"])
def create_report_job():
    """Start a one-shot Cursor agent job to author a Data report generator."""
    from alab_management.dashboard import report_agent

    data = request.get_json(silent=True) or {}
    try:
        job = report_agent.start_report_job(data.get("prompt"))
    except report_agent.ReportAgentError as exc:
        return jsonify({"status": "error", "errors": str(exc)}), exc.status_code
    except Exception as exc:
        return jsonify({"status": "error", "errors": str(exc)}), 400
    return jsonify({"status": "success", "job": make_jsonable(job)})


@data_bp.route("/report_jobs/current", methods=["GET"])
def current_report_job():
    """Return the latest/active report agent job (if any)."""
    from alab_management.dashboard import report_agent

    job = report_agent.get_current_job()
    return jsonify({"status": "success", "job": make_jsonable(job)})


@data_bp.route("/report_jobs/<job_id>", methods=["GET"])
def get_report_job(job_id: str):
    """Return status and log for a report agent job."""
    from alab_management.dashboard import report_agent

    job = report_agent.get_job(job_id)
    if job is None:
        return jsonify({"status": "error", "errors": f"Unknown job '{job_id}'."}), 404
    return jsonify({"status": "success", "job": make_jsonable(job)})


@data_bp.route("/sample_summary", methods=["GET"])
def sample_summary():
    """Return a curated sample summary for one calendar month."""
    try:
        window = _window_from_request()
    except ValueError as exc:
        return jsonify({"status": "error", "errors": str(exc)}), 400
    return jsonify(_response_payload(_sample_summary_rows(window), window))


@data_bp.route("/powder_dosing_actuals", methods=["GET"])
def powder_dosing_actuals():
    """Return a curated powder dosing export for one calendar month."""
    try:
        window = _window_from_request()
    except ValueError as exc:
        return jsonify({"status": "error", "errors": str(exc)}), 400
    return jsonify(_response_payload(_powder_dosing_rows(window), window))


@data_bp.route("/sample_report", methods=["GET"])
def sample_report():
    """Return collapsed sample reports for one calendar month."""
    try:
        window = _window_from_request()
    except ValueError as exc:
        return jsonify({"status": "error", "errors": str(exc)}), 400
    return jsonify(_response_payload(_sample_report_rows(window), window))


@data_bp.route("/task_outcome_log", methods=["GET"])
def task_outcome_log():
    """Return a curated task outcome log for one calendar month."""
    try:
        window = _window_from_request()
    except ValueError as exc:
        return jsonify({"status": "error", "errors": str(exc)}), 400
    return jsonify(_response_payload(_task_outcome_rows(window), window))


@data_bp.route("/sample_report.csv", methods=["GET"])
def sample_report_csv():
    """Download the collapsed sample report as CSV."""
    try:
        window = _window_from_request()
    except ValueError as exc:
        return jsonify({"status": "error", "errors": str(exc)}), 400
    rows = []
    for row in _sample_report_rows(window):
        rows.append(
            {
                "name": row["name"],
                "aliases": row["aliases"],
                "sample_ids": row["sample_ids"],
                "source_count": row["source_count"],
                "target": row["target"],
                "target_masses": row["target_masses"],
                "actual_masses": row["actual_masses"],
                "powder_summary": row["powder_summary"],
                "crucible": row["crucible"],
                "mixing_pot": row["mixing_pot"],
                "actual_transfer_mass": row["actual_transfer_mass"],
                "heating_temperature": row["heating_temperature"],
                "dwell_hours": row["dwell_hours"],
                "heating_done": row["heating_done"],
                "heating_source": row["heating_source"],
                "task_summary": row["task_summary"],
                "created_at": row["created_at"],
                "last_updated": row["last_updated"],
            }
        )
    return _csv_response("sample_report.csv", rows)


@data_bp.route("/sample_summary.csv", methods=["GET"])
def sample_summary_csv():
    """Download the sample summary as CSV."""
    try:
        window = _window_from_request()
    except ValueError as exc:
        return jsonify({"status": "error", "errors": str(exc)}), 400
    return _csv_response("sample_summary.csv", _sample_summary_rows(window))


@data_bp.route("/powder_dosing_actuals.csv", methods=["GET"])
def powder_dosing_actuals_csv():
    """Download powder dosing actuals as CSV."""
    try:
        window = _window_from_request()
    except ValueError as exc:
        return jsonify({"status": "error", "errors": str(exc)}), 400
    return _csv_response("powder_dosing_actuals.csv", _powder_dosing_rows(window))


@data_bp.route("/task_outcome_log.csv", methods=["GET"])
def task_outcome_log_csv():
    """Download the task outcome log as CSV."""
    try:
        window = _window_from_request()
    except ValueError as exc:
        return jsonify({"status": "error", "errors": str(exc)}), 400
    return _csv_response("task_outcome_log.csv", _task_outcome_rows(window))
