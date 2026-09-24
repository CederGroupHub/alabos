"""Tests for durable sample position + position_history behavior."""

from datetime import datetime
from types import SimpleNamespace
from unittest.mock import MagicMock

from bson import ObjectId

from alab_management.dashboard.routes.sample_positions import (
    _slot_summary,
    is_occupancy_host,
)
from alab_management.lab_reset import _clear_sample_ownership
from alab_management.sample_view.sample_view import (
    POSITION_HISTORY_MAX,
    SampleView,
    _position_history_entry,
)


def test_clear_sample_ownership_preserves_position():
    now = datetime.now()
    samples = MagicMock()
    samples.update_many.return_value.modified_count = 2
    sample_view = SimpleNamespace(_sample_collection=samples)

    modified = _clear_sample_ownership(sample_view, now)

    assert modified == 2
    filter_doc, update_doc = samples.update_many.call_args.args
    assert "position" not in update_doc["$set"]
    assert "last_position" not in update_doc["$set"]
    assert update_doc["$set"]["task_id"] is None
    assert update_doc["$set"]["in_transit"] is None
    assert not any("position" in clause for clause in filter_doc["$or"])


def test_position_history_entry_shape():
    entry = _position_history_entry(
        "moved",
        "DASH_input_rack/slot/1",
        task_id=ObjectId(),
        destination="DASH_consumable_rack_A/vial_slot/2",
    )
    assert entry["event"] == "moved"
    assert entry["position"] == "DASH_input_rack/slot/1"
    assert entry["destination"].endswith("vial_slot/2")
    assert "at" in entry
    assert "task_id" in entry


def test_move_sample_appends_history_and_caps(monkeypatch):
    sample_id = ObjectId()
    collection = MagicMock()
    collection.find_one.return_value = {
        "_id": sample_id,
        "name": "s1",
        "position": "DASH_input_rack/slot/1",
        "task_id": None,
        "in_transit": None,
        "last_position": "DASH_input_rack/slot/1",
        "position_history": [],
    }
    collection.update_one.return_value = MagicMock()

    view = SampleView.__new__(SampleView)
    view._sample_collection = collection
    view._sample_positions_collection = MagicMock()
    view._lock = MagicMock()
    monkeypatch.setattr(view, "is_unoccupied_position", lambda _position: True)

    view.move_sample(sample_id, "DASH_input_rack/slot/2")

    _filter, update = collection.update_one.call_args.args
    assert update["$set"]["position"] == "DASH_input_rack/slot/2"
    push = update["$push"]["position_history"]
    assert push["$each"][0]["event"] == "moved"
    assert push["$slice"] == -POSITION_HISTORY_MAX


def test_create_sample_records_placed_history(monkeypatch):
    collection = MagicMock()
    collection.insert_one.return_value = SimpleNamespace(inserted_id=ObjectId())

    view = SampleView.__new__(SampleView)
    view._sample_collection = collection
    view._sample_positions_collection = MagicMock()
    view._lock = MagicMock()
    monkeypatch.setattr(view, "is_unoccupied_position", lambda _position: True)
    monkeypatch.setattr(view, "exists", lambda _sample_id: True)

    view.create_sample("demo", position="DASH_input_rack/slot/3")

    entry = collection.insert_one.call_args.args[0]
    assert entry["position"] == "DASH_input_rack/slot/3"
    assert entry["position_history"][0]["event"] == "placed"
    assert entry["position_history"][0]["position"] == "DASH_input_rack/slot/3"


def test_move_sample_clear_records_cleared_event(monkeypatch):
    sample_id = ObjectId()
    collection = MagicMock()
    collection.find_one.return_value = {
        "_id": sample_id,
        "name": "s1",
        "position": "DASH_input_rack/slot/1",
        "task_id": None,
        "in_transit": None,
        "last_position": "DASH_input_rack/slot/1",
    }

    view = SampleView.__new__(SampleView)
    view._sample_collection = collection
    view._sample_positions_collection = MagicMock()
    view._lock = MagicMock()

    view.move_sample(sample_id, None)

    _filter, update = collection.update_one.call_args.args
    assert update["$set"]["position"] is None
    assert "last_position" not in update["$set"]
    assert update["$push"]["position_history"]["$each"][0]["event"] == "cleared"
    assert (
        update["$push"]["position_history"]["$each"][0]["position"]
        == "DASH_input_rack/slot/1"
    )


def test_is_occupancy_host_filters_non_powder_devices():
    assert is_occupancy_host("DASH_consumable_rack_A")
    assert is_occupancy_host("DASH_input_rack")
    assert is_occupancy_host("DASH_aeris_xrd")
    assert is_occupancy_host("DASH_arm_JEEVES")
    assert is_occupancy_host("DASH_capper")
    assert is_occupancy_host("MOBILE_arm_ALFRED")
    assert not is_occupancy_host("DASH_acrylic_disk_dispenser")
    assert not is_occupancy_host("DASH_ball_dispenser")
    assert not is_occupancy_host("DASH_trash_bucket")
    assert not is_occupancy_host("DASH_petri_dish_dispenser")


def test_powder_slot_types_hide_caps():
    from alab_management.dashboard.routes.sample_positions import (
        is_powder_sample_slot_type,
    )

    assert is_powder_sample_slot_type("vial_slot")
    assert is_powder_sample_slot_type("crucible_slot")
    assert is_powder_sample_slot_type("slot")
    assert is_powder_sample_slot_type("gripper")
    assert not is_powder_sample_slot_type("ncap_slot")
    assert not is_powder_sample_slot_type("scap_slot")
    assert not is_powder_sample_slot_type("cap_slot")


def test_slot_summary_counts():
    summary = _slot_summary(
        {
            "vial_slot": [
                {"status": "OCCUPIED", "sample": {"in_transit": None}},
                {"status": "OCCUPIED", "sample": {"in_transit": {"source": "a"}}},
                {"status": "LOCKED", "sample": None},
                {"status": "EMPTY", "sample": None},
            ]
        }
    )
    assert summary == {
        "occupied": 2,
        "locked": 1,
        "in_transit": 1,
        "empty": 1,
        "slot_count": 4,
        "blocked_count": 0,
    }


def test_campaign_and_ownership_fields():
    from alab_management.dashboard.routes.sample_positions import (
        campaign_from_tags,
        ownership_fields,
    )

    assert campaign_from_tags(["campaign::hitrate", "other"]) == "hitrate"
    assert campaign_from_tags(["campaign:shake_xrd"]) == "shake_xrd"
    assert campaign_from_tags(["unrelated"]) is None

    fields = ownership_fields(
        tags=["campaign::demo"],
        metadata={"user": "Alice", "project": "P1"},
    )
    assert fields["campaign"] == "demo"
    assert fields["owner"] == "Alice"
    assert fields["project"] == "P1"

    fields_meta_campaign = ownership_fields(
        tags=[],
        metadata={"campaign": "from_meta", "submitter": "Bob"},
    )
    assert fields_meta_campaign["campaign"] == "from_meta"
    assert fields_meta_campaign["owner"] == "Bob"
