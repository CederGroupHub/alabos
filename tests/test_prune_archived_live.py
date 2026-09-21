"""Tests for pruning archived unplaced docs from live Alab."""

from types import SimpleNamespace
from unittest.mock import MagicMock

from bson import ObjectId

from alab_management.lab_reset import prune_archived_unplaced_from_live


def _completed_lookup(present_ids):
    """Return a collection mock whose find_one is True only for present_ids."""
    present = set(present_ids)

    def find_one(query, projection=None):
        doc_id = query.get("_id")
        return {"_id": doc_id} if doc_id in present else None

    return SimpleNamespace(find_one=find_one)


def test_prune_noop_without_completed_config(monkeypatch):
    monkeypatch.setattr("alab_management.lab_reset.AlabOSConfig", lambda: {})
    summary = prune_archived_unplaced_from_live()
    assert summary["samples_pruned"] == 0
    assert summary["experiments_pruned"] == 0


def test_prune_deletes_unplaced_archived_sample_and_experiment(monkeypatch):
    sample_id = ObjectId()
    task_id = ObjectId()
    exp_id = ObjectId()

    live_samples = MagicMock()
    live_samples.find.return_value = [
        {"_id": sample_id, "position": None, "in_transit": None}
    ]

    live_tasks = MagicMock()
    live_tasks.find.return_value = [{"_id": task_id}]

    live_experiments = MagicMock()
    live_experiments.find.return_value = [
        {
            "_id": exp_id,
            "status": "CANCELLED",
            "samples": [{"sample_id": sample_id}],
            "tasks": [{"task_id": task_id}],
        }
    ]

    monkeypatch.setattr(
        "alab_management.lab_reset.AlabOSConfig",
        lambda: {"mongodb_completed": {}},
    )
    monkeypatch.setattr(
        "alab_management.lab_reset.get_completed_collection",
        lambda name: {
            "samples": _completed_lookup([sample_id]),
            "tasks": _completed_lookup([task_id]),
            "experiment": _completed_lookup([exp_id]),
        }[name],
    )
    monkeypatch.setattr(
        "alab_management.lab_reset.SampleView",
        lambda: SimpleNamespace(_sample_collection=live_samples),
    )
    monkeypatch.setattr(
        "alab_management.lab_reset.TaskView",
        lambda: SimpleNamespace(_task_collection=live_tasks),
    )
    monkeypatch.setattr(
        "alab_management.lab_reset.ExperimentView",
        lambda: SimpleNamespace(_experiment_collection=live_experiments),
    )

    summary = prune_archived_unplaced_from_live()

    assert summary["samples_pruned"] == 1
    assert summary["tasks_pruned"] == 1
    assert summary["experiments_pruned"] == 1
    assert summary["skipped_not_in_completed"] == 0
    live_samples.delete_one.assert_called_once_with({"_id": sample_id})
    live_tasks.delete_one.assert_called_once_with({"_id": task_id})
    live_experiments.delete_one.assert_called_once_with({"_id": exp_id})


def test_prune_skips_sample_missing_from_completed(monkeypatch):
    sample_id = ObjectId()
    exp_id = ObjectId()

    live_samples = MagicMock()
    live_samples.find.return_value = [
        {"_id": sample_id, "position": None, "in_transit": None}
    ]
    live_samples.count_documents.return_value = 1

    live_tasks = MagicMock()
    live_tasks.find.return_value = []

    live_experiments = MagicMock()
    live_experiments.find.return_value = [
        {
            "_id": exp_id,
            "status": "CANCELLED",
            "samples": [{"sample_id": sample_id}],
            "tasks": [],
        }
    ]

    monkeypatch.setattr(
        "alab_management.lab_reset.AlabOSConfig",
        lambda: {"mongodb_completed": {}},
    )
    monkeypatch.setattr(
        "alab_management.lab_reset.get_completed_collection",
        lambda name: {
            "samples": _completed_lookup([]),  # sample NOT in completed
            "tasks": _completed_lookup([]),
            "experiment": _completed_lookup([exp_id]),
        }[name],
    )
    monkeypatch.setattr(
        "alab_management.lab_reset.SampleView",
        lambda: SimpleNamespace(_sample_collection=live_samples),
    )
    monkeypatch.setattr(
        "alab_management.lab_reset.TaskView",
        lambda: SimpleNamespace(_task_collection=live_tasks),
    )
    monkeypatch.setattr(
        "alab_management.lab_reset.ExperimentView",
        lambda: SimpleNamespace(_experiment_collection=live_experiments),
    )

    summary = prune_archived_unplaced_from_live()

    assert summary["samples_pruned"] == 0
    assert summary["skipped_not_in_completed"] >= 1
    live_samples.delete_one.assert_not_called()
    live_experiments.delete_one.assert_not_called()


def test_prune_skips_task_missing_from_completed(monkeypatch):
    sample_id = ObjectId()
    task_id = ObjectId()
    exp_id = ObjectId()

    live_samples = MagicMock()
    live_samples.find.return_value = [{"_id": sample_id, "position": None, "in_transit": None}]

    live_tasks = MagicMock()
    live_tasks.find.return_value = [{"_id": task_id}]

    live_experiments = MagicMock()
    live_experiments.find.return_value = [
        {
            "_id": exp_id,
            "status": "COMPLETED",
            "samples": [{"sample_id": sample_id}],
            "tasks": [{"task_id": task_id}],
        }
    ]

    monkeypatch.setattr(
        "alab_management.lab_reset.AlabOSConfig",
        lambda: {"mongodb_completed": {}},
    )
    monkeypatch.setattr(
        "alab_management.lab_reset.get_completed_collection",
        lambda name: {
            "samples": _completed_lookup([sample_id]),
            "tasks": _completed_lookup([]),  # task NOT archived
            "experiment": _completed_lookup([exp_id]),
        }[name],
    )
    monkeypatch.setattr(
        "alab_management.lab_reset.SampleView",
        lambda: SimpleNamespace(_sample_collection=live_samples),
    )
    monkeypatch.setattr(
        "alab_management.lab_reset.TaskView",
        lambda: SimpleNamespace(_task_collection=live_tasks),
    )
    monkeypatch.setattr(
        "alab_management.lab_reset.ExperimentView",
        lambda: SimpleNamespace(_experiment_collection=live_experiments),
    )

    summary = prune_archived_unplaced_from_live()

    # Samples stay until the whole experiment unit is safe to remove.
    assert summary["samples_pruned"] == 0
    assert summary["tasks_pruned"] == 0
    assert summary["experiments_pruned"] == 0
    live_samples.delete_one.assert_not_called()
    live_tasks.delete_one.assert_not_called()
    live_experiments.delete_one.assert_not_called()


def test_prune_skips_experiment_missing_from_completed(monkeypatch):
    sample_id = ObjectId()
    exp_id = ObjectId()

    live_samples = MagicMock()
    live_samples.find.return_value = [{"_id": sample_id, "position": None, "in_transit": None}]

    live_tasks = MagicMock()
    live_tasks.find.return_value = []

    live_experiments = MagicMock()
    live_experiments.find.return_value = [
        {
            "_id": exp_id,
            "status": "CANCELLED",
            "samples": [{"sample_id": sample_id}],
            "tasks": [],
        }
    ]

    monkeypatch.setattr(
        "alab_management.lab_reset.AlabOSConfig",
        lambda: {"mongodb_completed": {}},
    )
    monkeypatch.setattr(
        "alab_management.lab_reset.get_completed_collection",
        lambda name: {
            "samples": _completed_lookup([sample_id]),
            "tasks": _completed_lookup([]),
            "experiment": _completed_lookup([]),  # experiment NOT archived
        }[name],
    )
    monkeypatch.setattr(
        "alab_management.lab_reset.SampleView",
        lambda: SimpleNamespace(_sample_collection=live_samples),
    )
    monkeypatch.setattr(
        "alab_management.lab_reset.TaskView",
        lambda: SimpleNamespace(_task_collection=live_tasks),
    )
    monkeypatch.setattr(
        "alab_management.lab_reset.ExperimentView",
        lambda: SimpleNamespace(_experiment_collection=live_experiments),
    )

    summary = prune_archived_unplaced_from_live()

    # Sample needs archived parent experiment — skipped
    assert summary["samples_pruned"] == 0
    assert summary["experiments_pruned"] == 0
    live_samples.delete_one.assert_not_called()
    live_experiments.delete_one.assert_not_called()


def test_prune_leaves_placed_samples(monkeypatch):
    """Still-placed samples keep the live experiment from being pruned."""
    sample_id = ObjectId()
    exp_id = ObjectId()
    live_samples = MagicMock()
    live_samples.find.return_value = [
        {
            "_id": sample_id,
            "position": "DASH_input_rack/slot/1",
            "in_transit": None,
        }
    ]

    live_tasks = MagicMock()
    live_tasks.find.return_value = []
    live_experiments = MagicMock()
    live_experiments.find.return_value = [
        {
            "_id": exp_id,
            "status": "CANCELLED",
            "samples": [{"sample_id": sample_id}],
            "tasks": [],
        }
    ]

    monkeypatch.setattr(
        "alab_management.lab_reset.AlabOSConfig",
        lambda: {"mongodb_completed": {}},
    )
    monkeypatch.setattr(
        "alab_management.lab_reset.get_completed_collection",
        lambda name: {
            "samples": _completed_lookup([sample_id]),
            "tasks": _completed_lookup([]),
            "experiment": _completed_lookup([exp_id]),
        }[name],
    )
    monkeypatch.setattr(
        "alab_management.lab_reset.SampleView",
        lambda: SimpleNamespace(_sample_collection=live_samples),
    )
    monkeypatch.setattr(
        "alab_management.lab_reset.TaskView",
        lambda: SimpleNamespace(_task_collection=live_tasks),
    )
    monkeypatch.setattr(
        "alab_management.lab_reset.ExperimentView",
        lambda: SimpleNamespace(_experiment_collection=live_experiments),
    )

    summary = prune_archived_unplaced_from_live()
    assert summary["samples_pruned"] == 0
    assert summary["experiments_pruned"] == 0
    live_samples.delete_one.assert_not_called()
    live_experiments.delete_one.assert_not_called()
