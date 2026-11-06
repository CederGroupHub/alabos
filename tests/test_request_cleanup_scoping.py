"""Unit tests for request_cleanup sample scoping and non-blocking restart cleanup."""

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from bson import ObjectId

from alab_management.lab_view import LabView
from alab_management.task_view.task_enums import TaskStatus
from alab_management.user_input import SUPERSEDED_RESPONSE, UserRequestStatus


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
    assert lab_view.request_user_input.call_args.kwargs["request_context_extra"] == {
        "cleanup": True
    }


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


def test_arm_restart_cleanup_posts_without_blocking():
    s1 = ObjectId()
    lab_view = _lab_view_with_samples(
        [{"_id": s1, "name": "A", "position": "rack/1"}]
    )
    request_id = ObjectId()
    mock_view = MagicMock()
    mock_view.insert_request.return_value = request_id

    with patch("alab_management.lab_view.UserInputView", return_value=mock_view):
        result = lab_view.arm_restart_cleanup(clear_positions=True)

    assert result == request_id
    lab_view.move_sample.assert_not_called()
    lab_view._resource_requester.release_all_resources.assert_not_called()
    kwargs = mock_view.insert_request.call_args.kwargs
    assert kwargs["task_id"] == lab_view.task_id
    assert kwargs["options"] == ["OK"]
    assert kwargs["request_context_extra"]["restart_cleanup"] is True
    assert kwargs["request_context_extra"]["clear_positions"] is True
    assert kwargs["request_context_extra"]["sample_ids"] == [str(s1)]
    assert "unrecoverable error" in kwargs["prompt"].lower()


def test_clean_up_tasks_from_previous_runs_is_nonblocking():
    from alab_management.task_manager.task_manager import TaskManager

    s1 = ObjectId()
    task_id = ObjectId()
    initiated_id = ObjectId()
    lab_view = _lab_view_with_samples(
        [{"_id": s1, "name": "A", "position": "LABMAN_quadrant_3/processing/1"}]
    )
    lab_view._task_id = task_id
    lab_view.arm_restart_cleanup = MagicMock(return_value=ObjectId())

    manager = TaskManager.__new__(TaskManager)
    manager.task_view = MagicMock()

    def get_by_status(status):
        name = status.name if hasattr(status, "name") else str(status)
        if name == "RUNNING":
            return [{"task_id": task_id, "type": type("PowderDosing", (), {})}]
        if name == "INITIATED":
            return [{"task_id": initiated_id, "type": type("Heating", (), {})}]
        return []

    manager.task_view.get_tasks_by_status.side_effect = get_by_status

    with patch(
        "alab_management.task_manager.task_manager.LabView",
        return_value=lab_view,
    ):
        manager.clean_up_tasks_from_previous_runs()

    lab_view.arm_restart_cleanup.assert_called_once_with(clear_positions=False)
    lab_view.move_sample.assert_not_called()
    # Task stays RUNNING until dashboard OK; only INITIATED → READY now.
    status_calls = manager.task_view.update_status.call_args_list
    assert any(
        call.kwargs["task_id"] == initiated_id
        and call.kwargs["status"] == TaskStatus.READY
        for call in status_calls
    )
    assert not any(
        call.kwargs.get("status") == TaskStatus.CANCELLED for call in status_calls
    )


def test_restart_cleanup_completer_releases_and_cancels():
    from alab_management.dashboard.restart_cleanup import (
        handle_restart_cleanup_user_input_response,
    )

    s1 = ObjectId()
    task_id = ObjectId()
    lab_view = _lab_view_with_samples(
        [{"_id": s1, "name": "A", "position": "rack/1"}]
    )
    lab_view._task_id = task_id
    lab_view._LabView__task_entry["_id"] = task_id
    lab_view._LabView__task_entry["samples"] = [
        {"name": "A", "sample_id": s1}
    ]

    request_doc = {
        "_id": ObjectId(),
        "request_context": {
            "restart_cleanup": True,
            "clear_positions": True,
            "task_id": task_id,
            "sample_ids": [str(s1)],
        },
    }

    with (
        patch(
            "alab_management.dashboard.restart_cleanup.LabView",
            return_value=lab_view,
        ),
        patch(
            "alab_management.dashboard.restart_cleanup.TaskView"
        ) as mock_task_view_cls,
    ):
        mock_task_view = mock_task_view_cls.return_value
        handle_restart_cleanup_user_input_response(request_doc, "OK")

    lab_view.move_sample.assert_called_once_with(sample=s1, position=None)
    lab_view._resource_requester.release_all_resources.assert_called_once()
    mock_task_view.update_status.assert_called_once_with(
        task_id=task_id, status=TaskStatus.CANCELLED
    )


def test_restart_cleanup_completer_ignores_non_ok():
    from alab_management.dashboard.restart_cleanup import (
        handle_restart_cleanup_user_input_response,
    )

    request_doc = {
        "_id": ObjectId(),
        "request_context": {
            "restart_cleanup": True,
            "task_id": ObjectId(),
            "clear_positions": True,
        },
    }
    with patch("alab_management.dashboard.restart_cleanup.LabView") as mock_lv:
        handle_restart_cleanup_user_input_response(request_doc, SUPERSEDED_RESPONSE)
        mock_lv.assert_not_called()


def test_insert_request_supersedes_cleanup_for_same_task():
    from alab_management.user_input import UserInputView

    collection = MagicMock()
    update_result = MagicMock()
    update_result.modified_count = 1
    collection.update_many.return_value = update_result

    view = UserInputView.__new__(UserInputView)
    view._input_collection = collection
    view._task_view = MagicMock()
    view._experiment_view = MagicMock()
    view._experiment_view.get_experiment_by_task_id.return_value = {"_id": ObjectId()}
    view._alarm = MagicMock()

    task_id = ObjectId()
    view.insert_request(
        prompt="An unrecoverable error has occurred.\n\nWhat to do:\n(1) remove samples",
        options=["OK"],
        task_id=task_id,
        category="RestartCleanup",
        request_context_extra={
            "restart_cleanup": True,
            "cleanup": True,
            "clear_positions": True,
        },
    )

    collection.update_many.assert_called_once()
    query, update = collection.update_many.call_args.args
    assert query["status"] == UserRequestStatus.PENDING.value
    assert query["request_context.task_id"] == task_id
    assert update["$set"]["response"] == SUPERSEDED_RESPONSE
    collection.insert_one.assert_called_once()
