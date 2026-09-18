"""Tests for the dashboard Release locks & tasks software wipe."""

from types import SimpleNamespace
from unittest.mock import MagicMock

from bson import ObjectId

from alab_management.experiment_view.experiment_view import ExperimentStatus
from alab_management.lab_reset import reset_lab_software_state


def test_reset_lab_software_state_cancels_and_releases(monkeypatch):
    task_id = ObjectId()
    experiment_id = ObjectId()
    device_id = ObjectId()

    task_collection = MagicMock()
    task_collection.find.return_value = [
        {"_id": task_id, "status": "RUNNING", "task_actor_id": None},
    ]

    user_input_collection = MagicMock()
    user_input_collection.update_many.return_value.modified_count = 2

    device_collection = MagicMock()
    device_collection.find.return_value = [
        {
            "_id": device_id,
            "name": "MOBILE_arm_ALFRED",
            "status": "OCCUPIED",
            "attributes": {"pending_requests": {"a": 1}, "disabled": False},
        }
    ]

    sample_positions = MagicMock()
    sample_positions.update_many.return_value.modified_count = 3
    samples = MagicMock()
    samples.update_many.return_value.modified_count = 4

    experiment_view = MagicMock()
    experiment_view.get_experiments_with_status.side_effect = [
        [{"_id": experiment_id}],
        [],
    ]
    lock_collection = MagicMock()
    requests_collection = MagicMock()

    monkeypatch.setattr(
        "alab_management.lab_reset.TaskView",
        lambda: SimpleNamespace(_task_collection=task_collection),
    )
    monkeypatch.setattr("alab_management.lab_reset.ExperimentView", lambda: experiment_view)
    monkeypatch.setattr(
        "alab_management.lab_reset.DeviceView",
        lambda: SimpleNamespace(_device_collection=device_collection),
    )
    monkeypatch.setattr(
        "alab_management.lab_reset.SampleView",
        lambda: SimpleNamespace(
            _sample_positions_collection=sample_positions,
            _sample_collection=samples,
        ),
    )
    monkeypatch.setattr(
        "alab_management.lab_reset.UserInputView",
        lambda: SimpleNamespace(_input_collection=user_input_collection),
    )
    monkeypatch.setattr(
        "alab_management.lab_reset.get_collection",
        lambda name: lock_collection if name == "_lock" else requests_collection,
    )

    summary = reset_lab_software_state(settle_s=0)

    assert summary["tasks_cancelled"] == 1
    assert summary["user_inputs_dismissed"] == 2
    assert summary["devices_released"] == 1
    assert summary["positions_unlocked"] == 3
    assert summary["samples_unassigned"] == 4
    assert summary["experiments_closed"] == 1
    task_collection.update_many.assert_called_once()
    lock_collection.drop.assert_called_once()
    requests_collection.drop.assert_called_once()
    experiment_view.update_experiment_status.assert_called_once()
    assert (
        experiment_view.update_experiment_status.call_args.kwargs["status"]
        == ExperimentStatus.CANCELLED
    )
    dismiss_filter = user_input_collection.update_many.call_args.args[0]
    assert dismiss_filter["request_context.experiment_id"] == {"$exists": True}
    assert dismiss_filter["request_context.maintenance"] == {"$ne": True}
    assert device_collection.update_one.call_count == 2

    sample_filter, sample_update = samples.update_many.call_args.args
    assert sample_update["$set"]["task_id"] is None
    assert sample_update["$set"]["in_transit"] is None
    assert "position" not in sample_update["$set"]
    assert "last_position" not in sample_update["$set"]
    assert {"task_id": {"$ne": None}} in sample_filter["$or"]
    assert {"in_transit": {"$ne": None}} in sample_filter["$or"]
    assert not any("position" in clause for clause in sample_filter["$or"])


def test_get_lab_idle_status_reports_reasons(monkeypatch):
    from alab_management.lab_reset import get_lab_idle_status

    task_collection = MagicMock()
    task_collection.count_documents.return_value = 2
    sample_positions = MagicMock()
    sample_positions.count_documents.return_value = 1
    experiment_view = MagicMock()
    experiment_view.get_experiments_with_status.side_effect = [
        [{"_id": ObjectId()}],
        [],
    ]

    monkeypatch.setattr(
        "alab_management.lab_reset.TaskView",
        lambda: SimpleNamespace(_task_collection=task_collection),
    )
    monkeypatch.setattr(
        "alab_management.lab_reset.ExperimentView", lambda: experiment_view
    )
    monkeypatch.setattr(
        "alab_management.lab_reset.SampleView",
        lambda: SimpleNamespace(_sample_positions_collection=sample_positions),
    )

    status = get_lab_idle_status()
    assert status["idle"] is False
    assert any("live task" in r for r in status["reasons"])
    assert any("pending" in r for r in status["reasons"])
    assert any("reserved" in r for r in status["reasons"])


def test_clear_lab_occupancy_requires_idle(monkeypatch):
    from alab_management.lab_reset import LabNotIdleError, clear_lab_occupancy

    monkeypatch.setattr(
        "alab_management.lab_reset.get_lab_idle_status",
        lambda: {"idle": False, "reasons": ["1 live task(s)"]},
    )
    try:
        clear_lab_occupancy()
        raise AssertionError("expected LabNotIdleError")
    except LabNotIdleError as exc:
        assert exc.reasons == ["1 live task(s)"]


def test_clear_lab_occupancy_moves_samples(monkeypatch):
    from alab_management.lab_reset import clear_lab_occupancy

    sample_id = ObjectId()
    sample_view = MagicMock()
    sample_view._sample_collection.find.side_effect = [
        [{"_id": sample_id, "position": "furnace/1"}],
        [],
    ]
    sample_view._sample_positions_collection.update_many.return_value.modified_count = 0

    monkeypatch.setattr(
        "alab_management.lab_reset.get_lab_idle_status",
        lambda: {"idle": True, "reasons": []},
    )
    monkeypatch.setattr("alab_management.lab_reset.SampleView", lambda: sample_view)

    summary = clear_lab_occupancy()
    assert summary["samples_cleared"] == 1
    sample_view.move_sample.assert_called_once_with(sample_id, None)
