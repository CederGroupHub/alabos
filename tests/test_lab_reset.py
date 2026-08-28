"""Tests for the dashboard Reset lab software wipe."""

from types import SimpleNamespace
from unittest.mock import MagicMock

from bson import ObjectId

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
    assert device_collection.update_one.call_count == 2
