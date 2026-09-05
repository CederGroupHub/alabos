"""Backfill persistent location fields on existing sample documents."""

from typing import Any

from pymongo.collection import Collection

from alab_management.utils.data_objects import get_collection


def _backfill_fields(sample: dict[str, Any]) -> dict[str, Any]:
    updates: dict[str, Any] = {}

    if "last_position" not in sample:
        updates["last_position"] = sample.get("position")

    if "location_history" not in sample:
        updates["location_history"] = []

    if "location_state" not in sample:
        last_position = sample.get("last_position", sample.get("position"))
        if sample.get("in_transit") is not None:
            state = "in_transit"
        elif sample.get("position") is not None:
            state = "present"
        elif last_position is not None:
            state = "unconfirmed"
        else:
            state = "unknown"
        updates["location_state"] = state

    return updates


def backfill_sample_locations(
    *, dry_run: bool = False, collection: Collection | None = None
) -> dict[str, int]:
    """Populate missing location fields without inventing historical events."""
    samples = collection if collection is not None else get_collection("samples")
    summary = {"scanned": 0, "would_update": 0, "updated": 0}

    for sample in samples.find({}):
        summary["scanned"] += 1
        updates = _backfill_fields(sample)
        if not updates:
            continue
        summary["would_update"] += 1
        if dry_run:
            continue
        result = samples.update_one({"_id": sample["_id"]}, {"$set": updates})
        summary["updated"] += result.modified_count

    return summary
