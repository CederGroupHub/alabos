"""Curated data export routes for the dashboard."""

from __future__ import annotations

import csv
import io
from datetime import datetime
from typing import Any

from flask import Blueprint, Response, jsonify

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
        if completed.count_documents({}) > 0:
            return completed
    except ValueError:
        pass

    if name == "samples":
        return sample_view._sample_collection
    if name == "tasks":
        return task_view._task_collection
    raise ValueError(f"Unsupported history collection: {name}")


def _sample_id_str(sample_id: Any) -> str | None:
    return str(sample_id) if sample_id is not None else None


def _completed_sample_docs() -> dict[str, dict[str, Any]]:
    return {
        str(sample["_id"]): sample
        for sample in _get_history_collection("samples").find()
    }


def _tasks_by_sample_id() -> dict[str, list[dict[str, Any]]]:
    by_sample_id: dict[str, list[dict[str, Any]]] = {}
    for task in _get_history_collection("tasks").find():
        for sample in task.get("samples", []):
            sample_id = _sample_id_str(sample.get("sample_id"))
            if sample_id is None:
                continue
            by_sample_id.setdefault(sample_id, []).append(task)
    return by_sample_id


def _sample_metadata(sample_doc: dict[str, Any] | None) -> dict[str, Any]:
    return (sample_doc or {}).get("metadata") or {}


def _find_first_task_of_type(tasks: list[dict[str, Any]], task_type: str) -> dict[str, Any] | None:
    for task in tasks:
        if task.get("type") == task_type:
            return task
    return None


def _sample_summary_rows() -> list[dict[str, Any]]:
    rows = []
    for sample in _get_history_collection("samples").find().sort("created_at", 1):
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


def _powder_dosing_rows() -> list[dict[str, Any]]:
    rows = []
    sample_docs = _completed_sample_docs()
    tasks_by_sample_id = _tasks_by_sample_id()
    for task in _get_history_collection("tasks").find({"type": "PowderDosing"}).sort(
        "created_at", 1
    ):
        sample_lookup = {}
        for sample in task.get("samples", []):
            sample_name = sample.get("name")
            sample_id = _sample_id_str(sample.get("sample_id"))
            if sample_name:
                sample_lookup[sample_name] = {
                    "sample_id": sample_id,
                    "sample_doc": sample_docs.get(sample_id) if sample_id else None,
                }
        results_per_sample = (task.get("result") or {}).get("results_per_sample") or {}
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


def _task_outcome_rows() -> list[dict[str, Any]]:
    rows = []
    for task in _get_history_collection("tasks").find().sort("created_at", -1):
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
                "result_keys": sorted((task.get("result") or {}).keys()),
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


@data_bp.route("/sample_summary", methods=["GET"])
def sample_summary():
    """Return a curated sample summary."""
    return jsonify({"status": "success", "rows": make_jsonable(_sample_summary_rows())})


@data_bp.route("/powder_dosing_actuals", methods=["GET"])
def powder_dosing_actuals():
    """Return a curated powder dosing export."""
    return jsonify({"status": "success", "rows": make_jsonable(_powder_dosing_rows())})


@data_bp.route("/task_outcome_log", methods=["GET"])
def task_outcome_log():
    """Return a curated task outcome log."""
    return jsonify({"status": "success", "rows": make_jsonable(_task_outcome_rows())})


@data_bp.route("/sample_summary.csv", methods=["GET"])
def sample_summary_csv():
    """Download the sample summary as CSV."""
    return _csv_response("sample_summary.csv", _sample_summary_rows())


@data_bp.route("/powder_dosing_actuals.csv", methods=["GET"])
def powder_dosing_actuals_csv():
    """Download powder dosing actuals as CSV."""
    return _csv_response("powder_dosing_actuals.csv", _powder_dosing_rows())


@data_bp.route("/task_outcome_log.csv", methods=["GET"])
def task_outcome_log_csv():
    """Download the task outcome log as CSV."""
    return _csv_response("task_outcome_log.csv", _task_outcome_rows())
