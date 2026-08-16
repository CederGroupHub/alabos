"""Curated data export routes for the dashboard."""

from __future__ import annotations

import csv
import io
from datetime import datetime
from typing import Any

from flask import Blueprint, Response, jsonify

from alab_management.dashboard.lab_views import sample_view, task_view
from alab_management.utils.data_objects import make_jsonable

data_bp = Blueprint("/data", __name__, url_prefix="/api/data")


def _sample_summary_rows() -> list[dict[str, Any]]:
    rows = []
    for sample in sample_view._sample_collection.find().sort("created_at", 1):
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
    for sample in sample_view._sample_collection.find(
        {"metadata.powderdosing_results": {"$exists": True}}
    ).sort("created_at", 1):
        dosing = (sample.get("metadata") or {}).get("powderdosing_results") or {}
        powders = dosing.get("Powders") or []
        if not powders:
            rows.append(
                {
                    "sample_id": str(sample["_id"]),
                    "sample_name": sample["name"],
                    "position": sample.get("position"),
                    "last_position": sample.get("last_position"),
                    "mixing_pot_position": dosing.get("MixingPotPosition"),
                    "actual_transfer_mass": dosing.get("ActualTransferMass"),
                    "target_transfer_volume": dosing.get("TargetTransferVolume"),
                    "ethanol_dispense_volume": dosing.get("EthanolDispenseVolume"),
                    "powder_name": None,
                    "target_mass": None,
                    "dose_head_position": None,
                    "dose_mass": None,
                    "dose_timestamp": None,
                }
            )
            continue

        for powder in powders:
            doses = powder.get("Doses") or [None]
            for dose in doses:
                rows.append(
                    {
                        "sample_id": str(sample["_id"]),
                        "sample_name": sample["name"],
                        "position": sample.get("position"),
                        "last_position": sample.get("last_position"),
                        "mixing_pot_position": dosing.get("MixingPotPosition"),
                        "actual_transfer_mass": dosing.get("ActualTransferMass"),
                        "target_transfer_volume": dosing.get("TargetTransferVolume"),
                        "ethanol_dispense_volume": dosing.get("EthanolDispenseVolume"),
                        "powder_name": powder.get("PowderName"),
                        "target_mass": powder.get("TargetMass"),
                        "dose_head_position": None if dose is None else dose.get("HeadPosition"),
                        "dose_mass": None if dose is None else dose.get("Mass"),
                        "dose_timestamp": None if dose is None else dose.get("TimeStamp"),
                    }
                )
    return rows


def _task_outcome_rows() -> list[dict[str, Any]]:
    rows = []
    for task in task_view._task_collection.find().sort("created_at", -1):
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
