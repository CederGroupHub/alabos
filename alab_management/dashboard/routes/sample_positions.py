"""Lab-wide sample-position occupancy routes for the AlabOS dashboard."""

from __future__ import annotations

from typing import Any

from bson import ObjectId
from flask import Blueprint, request

from alab_management.dashboard.lab_views import experiment_view, sample_view
from alab_management.lab_reset import LabNotIdleError, get_lab_idle_status
from alab_management.utils.data_objects import get_completed_collection

sample_positions_bp = Blueprint(
    "/sample_positions", __name__, url_prefix="/api/sample-positions"
)

# Friendly labels for known devices; unknown devices fall back to a spaced name.
DISPLAY_NAMES: dict[str, str] = {
    "DASH_input_rack": "DASH Input Rack",
    "DASH_consumable_rack_A": "DASH Consumable Rack A",
    "DASH_consumable_rack_B": "DASH Consumable Rack B",
    "DASH_transfer_rack": "DASH Transfer Rack",
    "DASH_xrd_dispenser_rack": "DASH XRD Dispenser Rack",
    "DASH_dispenser_xrd_auto": "DASH XRD Dispenser (auto)",
    "DASH_dispenser_xrd_manual_A": "DASH XRD Dispenser (manual A)",
    "DASH_dispenser_xrd_manual_B": "DASH XRD Dispenser (manual B)",
    "DASH_aeris_xrd": "DASH Aeris XRD",
    "DASH_arm_JEEVES": "DASH Arm JEEVES",
    "DASH_capper": "DASH Capper",
    "MOBILE_arm_ALFRED": "Mobile Robot (ALFRED)",
    "BFT_input_rack": "BFT Input Rack",
}

# Preferred listing order.
DEVICE_PRIORITY_PREFIXES = ("DASH_", "MOBILE_", "LABMAN_", "BFT_")

# Slot path segments that hold caps / disks / other non-powder consumables — hide these.
# Vials, crucibles, XRD holders, robot grippers, Aeris slot, etc. stay visible.
_NON_POWDER_SLOT_TYPES = frozenset(
    {
        "ncap_slot",
        "scap_slot",
        "cap_slot",
        "ncap",
        "scap",
    }
)

# Whole devices that never hold a powder sample (vial/crucible/XRD holder).
_NON_POWDER_DEVICE_SUBSTRINGS = (
    "acrylic_disk",
    "petri_dish",
    "trash_bucket",
    "ball_dispenser",
    "cap_dispenser",
    "vial_labeler",
)


def _display_name(device_name: str) -> str:
    if device_name in DISPLAY_NAMES:
        return DISPLAY_NAMES[device_name]
    return device_name.replace("_", " ")


def _device_sort_key(device_name: str) -> tuple[int, str]:
    for index, prefix in enumerate(DEVICE_PRIORITY_PREFIXES):
        if device_name.startswith(prefix):
            return (index, device_name)
    return (len(DEVICE_PRIORITY_PREFIXES), device_name)


def is_powder_sample_device(device_name: str) -> bool:
    """False for devices that only dispense/hold non-powder consumables."""
    if not device_name:
        return False
    lower = device_name.lower()
    return not any(token in lower for token in _NON_POWDER_DEVICE_SUBSTRINGS)


def is_powder_sample_slot_type(position_type: str) -> bool:
    """False for cap / sieve-cap style slots that do not hold powder samples."""
    if not position_type:
        return True
    return position_type.lower() not in _NON_POWDER_SLOT_TYPES


# Back-compat alias used by older tests / callers.
def is_occupancy_host(device_name: str) -> bool:
    return is_powder_sample_device(device_name)


def _serialize_history(history: list[dict[str, Any]] | None) -> list[dict[str, Any]]:
    serialized: list[dict[str, Any]] = []
    for entry in history or []:
        item = {
            "at": entry.get("at").isoformat()
            if hasattr(entry.get("at"), "isoformat")
            else entry.get("at"),
            "position": entry.get("position"),
            "event": entry.get("event"),
        }
        if entry.get("task_id") is not None:
            item["task_id"] = str(entry["task_id"])
        if entry.get("destination") is not None:
            item["destination"] = entry["destination"]
        serialized.append(item)
    return serialized


def _serialize_in_transit(transit: dict[str, Any] | None) -> dict[str, Any] | None:
    if not transit:
        return None
    started_at = transit.get("started_at")
    return {
        "source": transit.get("source"),
        "destination": transit.get("destination"),
        "started_at": started_at.isoformat()
        if hasattr(started_at, "isoformat")
        else started_at,
    }


def campaign_from_tags(tags: list[Any] | None) -> str | None:
    """Extract campaign id from tags like ``campaign::hitrate``."""
    for tag in tags or []:
        if not isinstance(tag, str):
            continue
        lower = tag.lower()
        if lower.startswith("campaign::"):
            value = tag.split("::", 1)[1].strip()
            return value or tag
        if lower.startswith("campaign:"):
            value = tag.split(":", 1)[1].lstrip(":").strip()
            return value or tag
    return None


def ownership_fields(
    *,
    tags: list[Any] | None = None,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Campaign / owner / project from sample tags+metadata (experiment may fill campaign later)."""
    metadata = metadata or {}
    user = (
        metadata.get("user")
        or metadata.get("submitter")
        or metadata.get("owner")
        or metadata.get("submitted_by")
    )
    project = metadata.get("project")
    campaign = campaign_from_tags(tags)
    if not campaign and metadata.get("campaign") is not None:
        campaign = str(metadata["campaign"])
    return {
        "campaign": campaign,
        "owner": str(user) if user not in (None, "") else None,
        "project": str(project) if project not in (None, "") else None,
        "tags": list(tags or []),
    }


def _sample_to_dict(sample) -> dict[str, Any] | None:
    if sample is None:
        return None
    payload = {
        "sample_id": str(sample.sample_id),
        "name": sample.name,
        "position": sample.position,
        "last_position": sample.last_position,
        "task_id": str(sample.task_id) if sample.task_id else None,
        "in_transit": _serialize_in_transit(sample.in_transit),
        "position_history": _serialize_history(sample.position_history),
        "experiment_id": None,
        "experiment_name": None,
    }
    payload.update(
        ownership_fields(tags=sample.tags, metadata=sample.metadata)
    )
    return payload


def _sample_doc_to_dict(sample: dict[str, Any]) -> dict[str, Any]:
    payload = {
        "sample_id": str(sample["_id"]),
        "name": sample["name"],
        "position": sample.get("position"),
        "last_position": sample.get("last_position"),
        "task_id": str(sample["task_id"]) if sample.get("task_id") else None,
        "in_transit": _serialize_in_transit(sample.get("in_transit")),
        "position_history": _serialize_history(sample.get("position_history")),
        "experiment_id": None,
        "experiment_name": None,
    }
    payload.update(
        ownership_fields(
            tags=sample.get("tags"),
            metadata=sample.get("metadata") if isinstance(sample.get("metadata"), dict) else {},
        )
    )
    return payload


def _batch_experiment_info_by_sample_id(
    sample_ids: list[str],
) -> dict[str, dict[str, Any]]:
    """Map sample_id → experiment name/tags/campaign (live DB, then completed)."""
    object_ids: list[ObjectId] = []
    for sample_id in sample_ids:
        try:
            object_ids.append(ObjectId(sample_id))
        except Exception:
            continue
    if not object_ids:
        return {}

    info: dict[str, dict[str, Any]] = {}

    def _ingest(experiments) -> None:
        for experiment in experiments:
            campaign = campaign_from_tags(experiment.get("tags"))
            experiment_id = str(experiment["_id"])
            experiment_name = experiment.get("name")
            for entry in experiment.get("samples") or []:
                sid = entry.get("sample_id")
                if sid is None:
                    continue
                key = str(sid)
                if key in info:
                    continue
                info[key] = {
                    "experiment_id": experiment_id,
                    "experiment_name": experiment_name,
                    "campaign": campaign,
                }

    _ingest(
        experiment_view._experiment_collection.find(
            {"samples.sample_id": {"$in": object_ids}},
            {"name": 1, "tags": 1, "samples.sample_id": 1},
        )
    )

    missing = [oid for oid in object_ids if str(oid) not in info]
    if missing:
        try:
            completed = get_completed_collection("experiment")
            _ingest(
                completed.find(
                    {"samples.sample_id": {"$in": missing}},
                    {"name": 1, "tags": 1, "samples.sample_id": 1},
                )
            )
        except ValueError:
            pass

    return info


def _enrich_samples_with_experiment_info(samples: list[dict[str, Any]]) -> None:
    """Fill campaign / experiment fields in-place when missing on the sample."""
    ids = [sample["sample_id"] for sample in samples if sample.get("sample_id")]
    if not ids:
        return
    by_id = _batch_experiment_info_by_sample_id(ids)
    for sample in samples:
        info = by_id.get(sample["sample_id"])
        if not info:
            continue
        sample["experiment_id"] = info.get("experiment_id")
        sample["experiment_name"] = info.get("experiment_name")
        if not sample.get("campaign") and info.get("campaign"):
            sample["campaign"] = info["campaign"]


def _collect_samples_from_racks(racks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    samples: list[dict[str, Any]] = []
    for rack in racks:
        for slots in rack["slot_groups"].values():
            for slot in slots:
                sample = slot.get("sample")
                if sample:
                    samples.append(sample)
    return samples


def _position_slot_number(position_name: str) -> int:
    try:
        return int(position_name.split("/")[-1])
    except ValueError:
        return 0


def _device_from_position(position: str | None) -> str | None:
    if not position:
        return None
    return position.split("/", 1)[0]


def _monitored_device_names() -> list[str]:
    """Return parent devices that can hold powder samples (vial/crucible/XRD/etc.)."""
    devices = sample_view._sample_positions_collection.distinct(
        "parent_device", {"parent_device": {"$ne": None}}
    )
    hosts = [
        name
        for name in devices
        if isinstance(name, str) and name and is_powder_sample_device(name)
    ]
    return sorted(hosts, key=_device_sort_key)


def _slot_summary(slot_groups: dict[str, list[dict[str, Any]]]) -> dict[str, int]:
    occupied = 0
    locked = 0
    in_transit = 0
    empty = 0
    blocked = 0
    slot_count = 0
    for slots in slot_groups.values():
        for slot in slots:
            slot_count += 1
            if slot.get("blocked"):
                blocked += 1
            if slot.get("sample") and slot["sample"].get("in_transit"):
                in_transit += 1
            if slot["status"] == "OCCUPIED":
                occupied += 1
            elif slot["status"] == "LOCKED":
                locked += 1
            else:
                empty += 1
    return {
        "occupied": occupied,
        "locked": locked,
        "in_transit": in_transit,
        "empty": empty,
        "slot_count": slot_count,
        "blocked_count": blocked,
    }


def _rack_payload(device_name: str) -> dict[str, Any]:
    positions = sample_view.get_sample_positions_names_by_device(device_name)
    slot_groups: dict[str, list[dict[str, Any]]] = {}

    for position_name in positions:
        parts = position_name.split("/")
        if len(parts) < 2:
            continue
        # Prefer type segment (device/type/n); fall back to bare device/n as "slot".
        position_type = parts[-2] if len(parts) >= 3 else "slot"
        if not is_powder_sample_slot_type(position_type):
            continue

        sample = sample_view.get_sample_by_position(position_name)
        status, task_id = sample_view.get_sample_position_status(position_name)
        position_doc = sample_view.get_sample_position(position_name) or {}
        blocked = bool(position_doc.get("blocked"))
        blocked_at = position_doc.get("blocked_at")
        slot_groups.setdefault(position_type, []).append(
            {
                "name": position_name,
                "slot_number": _position_slot_number(position_name),
                "status": status.name,
                "locked_by_task_id": str(task_id) if task_id else None,
                "blocked": blocked,
                "blocked_reason": position_doc.get("blocked_reason"),
                "blocked_at": (
                    blocked_at.isoformat()
                    if hasattr(blocked_at, "isoformat")
                    else blocked_at
                ),
                "can_toggle_block": task_id is None,
                "sample": _sample_to_dict(sample),
            }
        )

    for entries in slot_groups.values():
        entries.sort(key=lambda entry: entry["slot_number"])

    summary = _slot_summary(slot_groups)
    slot_count = summary["slot_count"]
    blocked_count = summary["blocked_count"]
    return {
        "device_name": device_name,
        "display_name": _display_name(device_name),
        "slot_groups": slot_groups,
        "summary": summary,
        "slot_count": slot_count,
        "blocked_count": blocked_count,
        "all_blocked": slot_count > 0 and blocked_count == slot_count,
    }


def _unplaced_samples() -> list[dict[str, Any]]:
    samples = []
    for sample in sample_view._sample_collection.find({"position": None}).sort("name", 1):
        samples.append(_sample_doc_to_dict(sample))
    return samples


def _in_transit_samples() -> list[dict[str, Any]]:
    samples = []
    for entry in sample_view.get_in_transit_samples():
        started_at = entry.get("started_at")
        device_name = _device_from_position(
            entry.get("position") or entry.get("source") or entry.get("last_position")
        )
        samples.append(
            {
                "sample_id": str(entry["sample_id"]),
                "name": entry["name"],
                "position": entry.get("position"),
                "last_position": entry.get("last_position"),
                "task_id": str(entry["task_id"]) if entry.get("task_id") else None,
                "source": entry.get("source"),
                "destination": entry.get("destination"),
                "device_name": device_name,
                "started_at": started_at.isoformat()
                if hasattr(started_at, "isoformat")
                else started_at,
            }
        )
    return samples


def _live_samples_from_racks(racks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Flatten placed samples on occupancy hosts for the Find sample UI."""
    samples: list[dict[str, Any]] = []
    for rack in racks:
        for slots in rack["slot_groups"].values():
            for slot in slots:
                sample = slot.get("sample")
                if not sample:
                    continue
                samples.append(
                    {
                        "sample_id": sample["sample_id"],
                        "name": sample["name"],
                        "position": sample["position"] or slot["name"],
                        "last_position": sample.get("last_position"),
                        "device_name": rack["device_name"],
                        "display_name": rack["display_name"],
                        "in_transit": sample.get("in_transit"),
                        "position_history": sample.get("position_history") or [],
                        "status": slot["status"],
                        "campaign": sample.get("campaign"),
                        "owner": sample.get("owner"),
                        "project": sample.get("project"),
                        "experiment_id": sample.get("experiment_id"),
                        "experiment_name": sample.get("experiment_name"),
                        "tags": sample.get("tags") or [],
                    }
                )
    samples.sort(key=lambda entry: entry["name"].lower())
    return samples


@sample_positions_bp.route("/racks", methods=["GET"])
def get_racks():
    """Return powder-sample occupancy (hide cap-only / non-powder consumable slots)."""
    device_names = _monitored_device_names()
    racks = [_rack_payload(device_name) for device_name in device_names]
    racks = [rack for rack in racks if rack["slot_groups"]]
    unplaced = _unplaced_samples()
    placed = _collect_samples_from_racks(racks)
    _enrich_samples_with_experiment_info(placed + unplaced)
    return {
        "status": "success",
        "racks": racks,
        "live_samples": _live_samples_from_racks(racks),
        "unplaced_samples": unplaced,
        "in_transit_samples": _in_transit_samples(),
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
    """Remove a sample from the given rack slot (physical leave — clears position)."""
    idle = get_lab_idle_status()
    if not idle["idle"]:
        exc = LabNotIdleError(idle["reasons"])
        return (
            {
                "status": "error",
                "errors": str(exc),
                "reason": str(exc),
                "data": idle,
            },
            409,
        )

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


@sample_positions_bp.route("/block", methods=["POST"])
def block_position():
    """Mark a sample position blocked so automation will not assign it."""
    data = request.get_json(force=True)  # type: ignore[arg-type]
    position = data.get("position")
    if not position:
        return {"status": "error", "errors": "Missing required field `position`."}, 400

    reason = data.get("reason")
    try:
        sample_view.block_sample_position(position, reason=reason)
    except ValueError as exception:
        return {"status": "error", "errors": str(exception)}, 400
    except Exception as exception:
        return {"status": "error", "errors": str(exception)}, 400

    return {"status": "success"}


@sample_positions_bp.route("/unblock", methods=["POST"])
def unblock_position():
    """Clear the operator block on a sample position."""
    data = request.get_json(force=True)  # type: ignore[arg-type]
    position = data.get("position")
    if not position:
        return {"status": "error", "errors": "Missing required field `position`."}, 400

    try:
        sample_view.unblock_sample_position(position)
    except ValueError as exception:
        return {"status": "error", "errors": str(exception)}, 400
    except Exception as exception:
        return {"status": "error", "errors": str(exception)}, 400

    return {"status": "success"}


@sample_positions_bp.route("/unblock-all", methods=["POST"])
def unblock_all_positions():
    """Clear ``blocked`` on every sample position."""
    try:
        count = sample_view.unblock_all_sample_positions()
    except Exception as exception:
        return {"status": "error", "errors": str(exception)}, 400

    return {"status": "success", "unblocked_count": count}
