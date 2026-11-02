"""Regression: cancel during PENDING expansion must not be overwritten by RUNNING."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock

from bson import ObjectId

from alab_management.experiment_manager import ExperimentManager
from alab_management.experiment_view.experiment_view import ExperimentStatus


def _minimal_experiment(exp_id: ObjectId) -> dict:
    return {
        "_id": exp_id,
        "status": ExperimentStatus.PENDING.name,
        "samples": [{"name": "s1", "metadata": {}, "tags": []}],
        "tasks": [
            {
                "type": "Heating",
                "prev_tasks": [],
                "parameters": {},
                "samples": ["s1"],
            }
        ],
    }


def test_claim_pending_experiment_is_atomic():
    exp_id = ObjectId()
    collection = MagicMock()
    collection.find_one_and_update.return_value = {"_id": exp_id}
    view = SimpleNamespace(_experiment_collection=collection)

    from alab_management.experiment_view.experiment_view import ExperimentView

    claimed = ExperimentView.claim_pending_experiment(view, exp_id)
    assert claimed is True
    collection.find_one_and_update.assert_called_once_with(
        {"_id": exp_id, "status": ExperimentStatus.PENDING.name},
        {"$set": {"status": ExperimentStatus.RUNNING.name}},
    )

    collection.find_one_and_update.return_value = None
    assert ExperimentView.claim_pending_experiment(view, exp_id) is False


def test_try_update_experiment_status_respects_from_statuses():
    exp_id = ObjectId()
    collection = MagicMock()
    collection.update_one.return_value = SimpleNamespace(modified_count=1)
    view = SimpleNamespace(_experiment_collection=collection)

    from alab_management.experiment_view.experiment_view import ExperimentView

    ok = ExperimentView.try_update_experiment_status(
        view,
        exp_id,
        ExperimentStatus.ERROR,
        from_statuses=[ExperimentStatus.PENDING],
    )
    assert ok is True
    filter_arg = collection.update_one.call_args[0][0]
    assert filter_arg == {
        "_id": exp_id,
        "status": {"$in": [ExperimentStatus.PENDING.name]},
    }


def test_handle_pending_skips_when_claim_fails():
    exp_id = ObjectId()
    manager = ExperimentManager.__new__(ExperimentManager)
    manager.experiment_view = MagicMock()
    manager.sample_view = MagicMock()
    manager.task_view = MagicMock()
    manager.experiment_view.claim_pending_experiment.return_value = False

    started = manager._handle_pending_experiment(_minimal_experiment(exp_id))

    assert started is False
    manager.sample_view.create_sample.assert_not_called()
    manager.task_view.create_task.assert_not_called()
    manager.experiment_view.update_experiment_status.assert_not_called()


def test_handle_pending_aborts_tasks_if_cancelled_after_claim(monkeypatch):
    exp_id = ObjectId()
    task_id = ObjectId()
    manager = ExperimentManager.__new__(ExperimentManager)
    manager.experiment_view = MagicMock()
    manager.sample_view = MagicMock()
    manager.task_view = MagicMock()

    manager.experiment_view.claim_pending_experiment.return_value = True
    manager.sample_view.create_sample.return_value = ObjectId()
    manager.task_view.create_task.return_value = task_id
    # Cancel won after claim / during task creation.
    manager.experiment_view.get_experiment.return_value = {
        "_id": exp_id,
        "status": ExperimentStatus.CANCELLED.name,
    }

    force_cancel = MagicMock(return_value=1)
    monkeypatch.setattr(
        "alab_management.experiment_cancel._force_cancel_experiment_tasks",
        force_cancel,
    )

    started = manager._handle_pending_experiment(_minimal_experiment(exp_id))

    assert started is False
    manager.experiment_view.update_sample_task_id.assert_called_once()
    # Must not stomp CANCELLED with RUNNING.
    manager.experiment_view.update_experiment_status.assert_not_called()
    force_cancel.assert_called_once()
    assert force_cancel.call_args[0][1] == [task_id]


def test_handle_pending_returns_true_when_still_running_after_create():
    exp_id = ObjectId()
    task_id = ObjectId()
    manager = ExperimentManager.__new__(ExperimentManager)
    manager.experiment_view = MagicMock()
    manager.sample_view = MagicMock()
    manager.task_view = MagicMock()

    manager.experiment_view.claim_pending_experiment.return_value = True
    manager.sample_view.create_sample.return_value = ObjectId()
    manager.task_view.create_task.return_value = task_id
    manager.experiment_view.get_experiment.return_value = {
        "_id": exp_id,
        "status": ExperimentStatus.RUNNING.name,
    }

    started = manager._handle_pending_experiment(_minimal_experiment(exp_id))

    assert started is True
    manager.experiment_view.update_experiment_status.assert_not_called()
