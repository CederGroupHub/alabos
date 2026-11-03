"""Unit tests for request_cleanup sample scoping and mid-Labman soft cleanup."""

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from bson import ObjectId

from alab_management.lab_view import LabView


def _lab_view_with_samples(sample_docs: list[dict]) -> LabView:
    """Build a LabView with mocked persistence for cleanup tests."""
    task_id = ObjectId()
    samples = [
        {"name": doc["name"], "sample_id": doc["_id"]} for doc in sample_docs
    ]
    lab_view = LabView.__new__(LabView)
    lab_view._task_id = task_id
    lab_view._LabView__task_entry = {
        "_id": task_id,
        "samples": samples,
        "type": "PowderDosing",
    }
    sample_by_id = {doc["_id"]: SimpleNamespace(position=doc.get("position")) for doc in sample_docs}
    lab_view._sample_view = MagicMock()
    lab_view._sample_view.get_sample.side_effect = lambda sid: sample_by_id[sid]
    lab_view._sample_view.get_sample_positions_by_task.return_value = []
    lab_view._resource_requester = MagicMock()
    lab_view.request_user_input = MagicMock(return_value="OK")
    lab_view.move_sample = MagicMock()
    return lab_view


def test_occupies_only_labman_processing_true():
    s1, s2 = ObjectId(), ObjectId()
    lab_view = _lab_view_with_samples(
        [
            {"_id": s1, "name": "A", "position": "LABMAN_quadrant_3/processing/1"},
            {"_id": s2, "name": "B", "position": "LABMAN_quadrant_3/processing/2"},
        ]
    )
    assert lab_view.occupies_only_labman_processing() is True


def test_occupies_only_labman_processing_false_for_physical():
    s1, s2 = ObjectId(), ObjectId()
    lab_view = _lab_view_with_samples(
        [
            {"_id": s1, "name": "A", "position": "LABMAN_quadrant_3/processing/1"},
            {"_id": s2, "name": "B", "position": "LABMAN_quadrant_3/crucible/SubRackA/1"},
        ]
    )
    assert lab_view.occupies_only_labman_processing() is False


def test_occupies_only_labman_processing_false_when_empty():
    lab_view = _lab_view_with_samples(
        [{"_id": ObjectId(), "name": "A", "position": None}]
    )
    assert lab_view.occupies_only_labman_processing() is False


def test_request_cleanup_clears_all_by_default():
    s1, s2 = ObjectId(), ObjectId()
    lab_view = _lab_view_with_samples(
        [
            {"_id": s1, "name": "A", "position": "rack/1"},
            {"_id": s2, "name": "B", "position": "rack/2"},
        ]
    )
    lab_view.request_cleanup()
    assert lab_view.move_sample.call_count == 2
    positions = [call.kwargs.get("position") for call in lab_view.move_sample.call_args_list]
    assert positions == [None, None]
    lab_view._resource_requester.release_all_resources.assert_called_once()
    prompt = lab_view.request_user_input.call_args.kwargs["prompt"]
    assert "unrecoverable error" in prompt.lower()
    assert "rack/1" in prompt and "rack/2" in prompt


def test_request_cleanup_respects_sample_subset():
    s1, s2 = ObjectId(), ObjectId()
    lab_view = _lab_view_with_samples(
        [
            {"_id": s1, "name": "A", "position": "rack/1"},
            {"_id": s2, "name": "B", "position": "rack/2"},
        ]
    )
    lab_view.request_cleanup(samples=[{"name": "A", "sample_id": s1}])
    assert lab_view.move_sample.call_count == 1
    assert lab_view.move_sample.call_args.kwargs["sample"] == s1
    prompt = lab_view.request_user_input.call_args.kwargs["prompt"]
    assert "rack/1" in prompt
    assert "rack/2" not in prompt


def test_request_cleanup_soft_skips_clearing_positions():
    s1, s2 = ObjectId(), ObjectId()
    lab_view = _lab_view_with_samples(
        [
            {"_id": s1, "name": "A", "position": "LABMAN_quadrant_3/processing/1"},
            {"_id": s2, "name": "B", "position": "LABMAN_quadrant_3/processing/2"},
        ]
    )
    lab_view.request_cleanup(clear_positions=False)
    lab_view.move_sample.assert_not_called()
    lab_view._resource_requester.release_all_resources.assert_called_once()
    prompt = lab_view.request_user_input.call_args.kwargs["prompt"]
    assert "mid-Labman" in prompt
    assert "without clearing" in prompt


def test_restart_uses_soft_cleanup_for_processing_only():
    from alab_management.task_manager.task_manager import TaskManager

    s1 = ObjectId()
    task_id = ObjectId()
    lab_view = _lab_view_with_samples(
        [{"_id": s1, "name": "A", "position": "LABMAN_quadrant_3/processing/1"}]
    )
    lab_view._task_id = task_id

    manager = TaskManager.__new__(TaskManager)
    manager.task_view = MagicMock()
    manager.task_view.get_tasks_by_status.side_effect = lambda status: (
        [{"task_id": task_id, "type": type("PowderDosing", (), {})}]
        if status.name in {"RUNNING", "REQUESTING_RESOURCES"}
        else []
    )
    # INITIATED path
    def get_by_status(status):
        name = status.name if hasattr(status, "name") else str(status)
        if name in ("RUNNING", "REQUESTING_RESOURCES"):
            # Only return once for RUNNING
            if name == "RUNNING":
                return [{"task_id": task_id, "type": type("PowderDosing", (), {})}]
            return []
        return []

    manager.task_view.get_tasks_by_status.side_effect = get_by_status

    with patch(
        "alab_management.task_manager.task_manager.LabView",
        return_value=lab_view,
    ):
        manager.clean_up_tasks_from_previous_runs()

    lab_view.request_user_input.assert_called_once()
    prompt = lab_view.request_user_input.call_args.kwargs["prompt"]
    assert "mid-Labman" in prompt
    lab_view.move_sample.assert_not_called()
    manager.task_view.update_status.assert_called()
