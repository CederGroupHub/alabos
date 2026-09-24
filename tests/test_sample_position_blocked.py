"""Tests for durable sample-position ``blocked`` flag."""

from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from bson import ObjectId

from alab_management.sample_view.sample_view import SamplePositionStatus, SampleView


def _view_with_positions(docs_by_name: dict) -> SampleView:
    import re

    positions = MagicMock()

    def _matches_name_query(query_name, doc_name: str) -> bool:
        if isinstance(query_name, str):
            return doc_name == query_name
        if isinstance(query_name, dict) and "$regex" in query_name:
            return re.match(query_name["$regex"], doc_name) is not None
        return False

    def find_one(query, *args, **kwargs):
        for doc_name, doc in docs_by_name.items():
            if _matches_name_query(query.get("name"), doc_name):
                return doc
        return None

    def find(query, *args, **kwargs):
        results = []
        for doc_name, doc in docs_by_name.items():
            if not _matches_name_query(query.get("name"), doc_name):
                continue
            or_clauses = query.get("$or")
            if or_clauses:
                task_ok = any(
                    doc.get("task_id") == clause.get("task_id") for clause in or_clauses
                )
                if not task_ok:
                    continue
            results.append(doc)
        return results

    positions.find_one.side_effect = find_one
    positions.find.side_effect = find
    positions.update_one = MagicMock()
    positions.update_many = MagicMock(
        return_value=SimpleNamespace(modified_count=0)
    )

    view = SampleView.__new__(SampleView)
    view._sample_positions_collection = positions
    view._sample_collection = MagicMock()
    view._lock = MagicMock()
    return view


def test_get_available_skips_blocked():
    task_id = ObjectId()
    view = _view_with_positions(
        {
            "rack/slot/1": {
                "name": "rack/slot/1",
                "task_id": None,
                "blocked": True,
            },
            "rack/slot/2": {
                "name": "rack/slot/2",
                "task_id": None,
                "blocked": False,
            },
        }
    )
    view.get_sample_position_status = MagicMock(
        side_effect=lambda name: (SamplePositionStatus.EMPTY, None)
    )
    view.get_sample_position = MagicMock(
        side_effect=lambda name: view._sample_positions_collection.find_one(
            {"name": name}
        )
    )

    available = view.get_available_sample_position(
        task_id, position_prefix="rack/slot", exact_match=False
    )
    names = [entry["name"] for entry in available]
    assert names == ["rack/slot/2"]


def test_block_rejected_when_task_locked():
    view = _view_with_positions(
        {
            "rack/slot/1": {
                "name": "rack/slot/1",
                "task_id": ObjectId(),
                "blocked": False,
            }
        }
    )
    with pytest.raises(ValueError, match="locked by a task"):
        view.block_sample_position("rack/slot/1", reason="bad slot")
    view._sample_positions_collection.update_one.assert_not_called()


def test_unblock_rejected_when_task_locked():
    view = _view_with_positions(
        {
            "rack/slot/1": {
                "name": "rack/slot/1",
                "task_id": ObjectId(),
                "blocked": True,
            }
        }
    )
    with pytest.raises(ValueError, match="locked by a task"):
        view.unblock_sample_position("rack/slot/1")
    view._sample_positions_collection.update_one.assert_not_called()


def test_block_and_unblock_when_unlocked():
    view = _view_with_positions(
        {
            "rack/slot/1": {
                "name": "rack/slot/1",
                "task_id": None,
                "blocked": False,
            }
        }
    )
    view.block_sample_position("rack/slot/1", reason="jammed")
    set_doc = view._sample_positions_collection.update_one.call_args.args[1]["$set"]
    assert set_doc["blocked"] is True
    assert set_doc["blocked_reason"] == "jammed"
    assert set_doc["blocked_at"] is not None

    view.unblock_sample_position("rack/slot/1")
    set_doc = view._sample_positions_collection.update_one.call_args.args[1]["$set"]
    assert set_doc["blocked"] is False
    assert set_doc["blocked_reason"] is None
    assert set_doc["blocked_at"] is None


def test_unblock_all_only_clears_blocked():
    positions = MagicMock()
    positions.update_many.return_value = SimpleNamespace(modified_count=3)
    view = SampleView.__new__(SampleView)
    view._sample_positions_collection = positions

    count = view.unblock_all_sample_positions()
    assert count == 3
    filter_doc, update_doc = positions.update_many.call_args.args
    assert filter_doc == {"blocked": True}
    assert update_doc["$set"] == {
        "blocked": False,
        "blocked_reason": None,
        "blocked_at": None,
    }
    assert "task_id" not in update_doc["$set"]


def test_diagnose_includes_blocked_and_allow_unblock():
    task_id = ObjectId()
    view = _view_with_positions(
        {
            "rack/slot/1": {
                "name": "rack/slot/1",
                "task_id": None,
                "blocked": True,
                "blocked_reason": "broken",
            },
            "rack/slot/2": {
                "name": "rack/slot/2",
                "task_id": None,
                "blocked": False,
            },
        }
    )
    view.get_available_sample_position = MagicMock(return_value=[])
    view.get_sample_position_status = MagicMock(
        return_value=(SamplePositionStatus.EMPTY, None)
    )

    diagnosis = view.diagnose_sample_position_shortage(
        task_id,
        [{"prefix": "rack/slot", "number": 1}],
        exact_positions=set(),
    )
    assert diagnosis["allow_unblock_blocked"] is True
    assert diagnosis["allow_clear"] is False
    blockers = diagnosis["blocked_blockers"]
    assert len(blockers) == 1
    assert blockers[0]["reason"] == "BLOCKED"
    assert blockers[0]["position"] == "rack/slot/1"
    assert blockers[0]["blocked_reason"] == "broken"


def test_slot_summary_and_all_blocked():
    from alab_management.dashboard.routes.sample_positions import _slot_summary

    summary = _slot_summary(
        {
            "vial_slot": [
                {"status": "EMPTY", "blocked": True, "sample": None},
                {"status": "EMPTY", "blocked": True, "sample": None},
            ]
        }
    )
    assert summary["slot_count"] == 2
    assert summary["blocked_count"] == 2
    assert summary["slot_count"] > 0 and summary["blocked_count"] == summary["slot_count"]
