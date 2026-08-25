"""Manual sample-position management routes for a small set of racks."""

from __future__ import annotations

from typing import Any

from bson import ObjectId
from flask import Blueprint, request

from alab_management.dashboard.lab_views import sample_view

sample_positions_bp = Blueprint(
    "/sample_positions", __name__, url_prefix="/api/sample-positions"
)

MONITORED_RACKS = {
    "DASH_input_rack": {
        "position_prefixes": ["slot"],
        "display_name": "DASH Input Rack",
    },
    "DASH_consumable_rack_A": {
        "position_prefixes": ["vial_slot", "crucible_slot"],
        "display_name": "DASH Consumable Rack A",
    },
}


def _sample_to_dict(sample) -> dict[str, Any] | None:
    if sample is None:
        return None
    return {
        "sample_id": str(sample.sample_id),
        "name": sample.name,
        "position": sample.position,
        "last_position": sample.last_position,
        "task_id": str(sample.task_id) if sample.task_id else None,
    }


def _position_slot_number(position_name: str) -> int:
    try:
        return int(position_name.split("/")[-1])
    except ValueError:
        return 0


def _rack_payload(device_name: str) -> dict[str, Any]:
    config = MONITORED_RACKS[device_name]
    positions = sample_view.get_sample_positions_names_by_device(device_name)
    slot_groups: dict[str, list[dict[str, Any]]] = {
        prefix: [] for prefix in config["position_prefixes"]
    }

    for position_name in positions:
        parts = position_name.split("/")
        if len(parts) < 3:
            continue
        position_type = parts[-2]
        if position_type not in slot_groups:
            continue

        sample = sample_view.get_sample_by_position(position_name)
        status, task_id = sample_view.get_sample_position_status(position_name)
        slot_groups[position_type].append(
            {
                "name": position_name,
                "slot_number": _position_slot_number(position_name),
                "status": status.name,
                "locked_by_task_id": str(task_id) if task_id else None,
                "sample": _sample_to_dict(sample),
            }
        )

    for entries in slot_groups.values():
        entries.sort(key=lambda entry: entry["slot_number"])

    return {
        "device_name": device_name,
        "display_name": config["display_name"],
        "slot_groups": slot_groups,
    }


def _unplaced_samples() -> list[dict[str, Any]]:
    samples = []
    for sample in sample_view._sample_collection.find({"position": None}).sort("name", 1):
        samples.append(
            {
                "sample_id": str(sample["_id"]),
                "name": sample["name"],
                "last_position": sample.get("last_position"),
                "task_id": str(sample["task_id"]) if sample.get("task_id") else None,
            }
        )
    return samples


@sample_positions_bp.route("/racks", methods=["GET"])
def get_racks():
    """Return a curated rack-status view for manual editing."""
    return {
        "status": "success",
        "racks": [_rack_payload(device_name) for device_name in MONITORED_RACKS],
        "unplaced_samples": _unplaced_samples(),
    }


@sample_positions_bp.route("/place", methods=["POST"])
def place_sample():
    """Place an existing or new sample into a rack slot."""
    data = request.get_json(force=True)  # type: ignore[arg-type]
    position = data.get("position")
    sample_id = data.get("sample_id")
    sample_name = (data.get("sample_name") or "").strip()

    if not position:
        return {"status": "error", "errors": "Missing required field `position`."}, 400

    if sample_id:
        try:
            sample_view.move_sample(ObjectId(sample_id), position)
        except Exception as exception:
            return {"status": "error", "errors": str(exception)}, 400
    else:
        if not sample_name:
            return {
                "status": "error",
                "errors": "Provide either `sample_id` or `sample_name`.",
            }, 400
        try:
            sample_view.create_sample(name=sample_name, position=position)
        except Exception as exception:
            return {"status": "error", "errors": str(exception)}, 400

    return {"status": "success"}


@sample_positions_bp.route("/clear", methods=["POST"])
def clear_position():
    """Remove a sample from the given rack slot by moving it out of the rack."""
    data = request.get_json(force=True)  # type: ignore[arg-type]
    position = data.get("position")
    if not position:
        return {"status": "error", "errors": "Missing required field `position`."}, 400

    sample = sample_view.get_sample_by_position(position)
    if sample is None:
        return {"status": "error", "errors": f"No sample found at {position}."}, 400

    try:
        sample_view.move_sample(sample.sample_id, None)
    except Exception as exception:
        return {"status": "error", "errors": str(exception)}, 400

    return {"status": "success"}
