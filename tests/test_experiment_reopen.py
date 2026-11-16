"""Tests for experiment checkpoint resume / reopen."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
from bson import ObjectId

from alab_management.experiment_reopen import force_update_status, reopen_experiment_from_checkpoint
from alab_management.task_view.task_enums import TaskStatus


def test_force_update_status_bypasses_sticky_cancel():
    task_view = MagicMock()
    tid = ObjectId()
    force_update_status(task_view, tid, TaskStatus.READY)
    task_view._task_collection.update_one.assert_called_once()
    args = task_view._task_collection.update_one.call_args
    assert args[0][0] == {"_id": tid}
    assert args[0][1]["$set"]["status"] == "READY"


def test_reopen_requires_arm_home():
    with pytest.raises(ValueError, match="arm_home"):
        reopen_experiment_from_checkpoint(
            ObjectId(),
            task_id=ObjectId(),
            arm_home_confirmed=False,
        )


@patch("alab_management.experiment_reopen.ExperimentView")
@patch("alab_management.experiment_reopen.TaskView")
@patch("alab_management.experiment_reopen.SampleView")
def test_reopen_sets_ready(mock_sv, mock_tv, mock_ev):
    exp_id = ObjectId()
    task_id = ObjectId()
    sample_id = ObjectId()

    mock_ev.return_value.get_experiment.return_value = {
        "_id": exp_id,
        "status": "CANCELLED",
        "tasks": [task_id],
        "samples": [{"name": "s1", "sample_id": sample_id}],
    }
    mock_tv.return_value.get_task.return_value = {
        "_id": task_id,
        "status": "CANCELLED",
        "parameters": {},
        "samples": [{"name": "s1", "sample_id": sample_id}],
        "next_tasks": [],
    }
    mock_sv.return_value._sample_collection.find_one.return_value = {
        "_id": sample_id,
        "name": "s1",
    }

    result = reopen_experiment_from_checkpoint(
        exp_id,
        task_id=task_id,
        resume_from="RecoverCapShake",
        sample_positions={"s1": "DASH_input_rack/slot/1"},
        arm_home_confirmed=True,
    )
    assert result["task_status"] == "READY"
    assert result["resume_from"] == "RecoverCapShake"
    mock_sv.return_value.move_sample.assert_called()
    mock_ev.return_value._experiment_collection.update_one.assert_called()
