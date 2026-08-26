"""Curated data export routes for the dashboard."""

from __future__ import annotations

import csv
import io
from calendar import monthrange
from datetime import datetime
from typing import Any

from bson import ObjectId
from flask import Blueprint, Response, jsonify, request

from alab_management.dashboard.lab_views import sample_view, task_view
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


def _window_metadata(month_key: str) -> dict[str, Any]:
    start, end = _month_window(month_key)
    year, month = (int(part) for part in month_key.split("-"))
    tasks_col = _get_history_collection("tasks")
    has_older = (
        tasks_col.find_one({"created_at": {"$lt": start}}, projection={"_id": 1})
        is not None
    )
    current_month = _default_month_key()
    return {
        "month": month_key,
        "label": datetime(year, month, 1).strftime("%B %Y"),
        "start": start,
        "end": end,
        "has_older": has_older,
        "has_newer": month_key < current_month,
    }


def _window_from_request() -> dict[str, Any]:
    try:
        month_key = _parse_month_key(request.args.get("month"))
    except ValueError as exc:
        raise ValueError(str(exc)) from exc
    return _window_metadata(month_key)


def _created_at_filter(start: datetime, end: datetime) -> dict[str, Any]:
    return {"created_at": {"$gte": start, "$lt": end}}


def _response_payload(rows: list[dict[str, Any]], window: dict[str, Any]) -> dict[str, Any]:
    return {
        "status": "success",
        "window": make_jsonable(
            {
                "month": window["month"],
                "label": window["label"],
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
    """Return the active month window and whether older/newer months exist."""
    try:
        window = _window_from_request()
    except ValueError as exc:
        return jsonify({"status": "error", "errors": str(exc)}), 400
    return jsonify(
        {
            "status": "success",
            "window": make_jsonable(
                {
                    "month": window["month"],
                    "label": window["label"],
                    "has_older": window["has_older"],
                    "has_newer": window["has_newer"],
                    "older_month": _shift_month(window["month"], -1)
                    if window["has_older"]
                    else None,
                    "newer_month": _shift_month(window["month"], 1)
                    if window["has_newer"]
                    else None,
                }
            ),
        }
    )


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


@data_bp.route("/task_outcome_log", methods=["GET"])
def task_outcome_log():
    """Return a curated task outcome log for one calendar month."""
    try:
        window = _window_from_request()
    except ValueError as exc:
        return jsonify({"status": "error", "errors": str(exc)}), 400
    return jsonify(_response_payload(_task_outcome_rows(window), window))


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
