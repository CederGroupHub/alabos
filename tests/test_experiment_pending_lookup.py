"""Experiment GET must tolerate an experiment whose task documents do not exist yet.

An experiment is stored as PENDING at submit; its task documents appear about a second later, when the
ExperimentManager expands it. In that window every task id on the experiment row refers to nothing.
"""

from types import SimpleNamespace

from bson import ObjectId

from alab_management.dashboard.routes import experiment as experiment_routes
from alab_management.task_view.task_enums import TaskStatus


def _experiment(tasks, samples=None):
    return {
        "_id": ObjectId(),
        "name": "exp",
        "status": "PENDING",
        "submitted_at": None,
        "tasks": tasks,
        "samples": samples or [],
    }


def test_progress_is_zero_while_the_task_documents_are_missing(monkeypatch):
    exp = _experiment([{"task_id": ObjectId(), "type": "Heating"} for _ in range(3)])
    monkeypatch.setattr(
        experiment_routes,
        "experiment_view",
        SimpleNamespace(get_experiment=lambda _id: exp),
    )

    def missing(task_id):
        raise ValueError(f"No task exists with task_id: {task_id}")

    monkeypatch.setattr(
        experiment_routes, "task_view", SimpleNamespace(get_status=missing)
    )

    assert experiment_routes.get_experiment_progress(str(exp["_id"])) == (0.0, False)


def test_progress_counts_only_the_tasks_that_exist(monkeypatch):
    done, pending = ObjectId(), ObjectId()
    exp = _experiment([{"task_id": done}, {"task_id": pending}])
    monkeypatch.setattr(
        experiment_routes,
        "experiment_view",
        SimpleNamespace(get_experiment=lambda _id: exp),
    )

    def get_status(task_id):
        if task_id == done:
            return TaskStatus.COMPLETED
        raise ValueError("not created yet")

    monkeypatch.setattr(
        experiment_routes, "task_view", SimpleNamespace(get_status=get_status)
    )

    assert experiment_routes.get_experiment_progress(str(exp["_id"])) == (0.5, False)


def test_progress_does_not_divide_by_zero_without_tasks(monkeypatch):
    exp = _experiment([])
    monkeypatch.setattr(
        experiment_routes,
        "experiment_view",
        SimpleNamespace(get_experiment=lambda _id: exp),
    )

    assert experiment_routes.get_experiment_progress(str(exp["_id"])) == (0.0, False)


def test_progress_returns_a_pair_for_a_missing_experiment(monkeypatch):
    """Both callers unpack the result, so an error must not come back as a dict of its own key names."""
    monkeypatch.setattr(
        experiment_routes,
        "experiment_view",
        SimpleNamespace(get_experiment=lambda _id: None),
    )

    progress, error = experiment_routes.get_experiment_progress(str(ObjectId()))

    assert progress == 0.0
    assert error is False


def test_task_placeholder_keeps_what_the_experiment_row_knows(monkeypatch):
    task_id = ObjectId()
    monkeypatch.setattr(
        experiment_routes,
        "task_view",
        SimpleNamespace(get_task=lambda _id: (_ for _ in ()).throw(ValueError("gone"))),
    )

    doc = experiment_routes._task_doc_or_placeholder(
        {"task_id": task_id, "type": "Diffraction"}
    )

    assert doc == {"_id": task_id, "type": "Diffraction"}


def test_results_report_the_live_sample_metadata(monkeypatch):
    """The experiment row holds metadata as submitted; everything a task writes lands on the sample."""
    sample_id = ObjectId()
    monkeypatch.setattr(
        experiment_routes,
        "sample_view",
        SimpleNamespace(
            get_sample=lambda _id: SimpleNamespace(
                metadata={"target": "LiFePO4", "diffraction_results": {"rwp": 4.2}}
            )
        ),
    )

    metadata = experiment_routes._live_sample_metadata(
        {"sample_id": sample_id, "metadata": {"target": "LiFePO4"}}
    )

    assert metadata["diffraction_results"] == {"rwp": 4.2}


def test_results_fall_back_to_the_archived_sample_then_to_the_submitted_copy(monkeypatch):
    sample_id = ObjectId()

    def gone(_id):
        raise ValueError("pruned")

    monkeypatch.setattr(
        experiment_routes, "sample_view", SimpleNamespace(get_sample=gone)
    )
    monkeypatch.setattr(
        experiment_routes,
        "_completed_sample_doc",
        lambda _id: {"metadata": {"heating_results": {"ok": True}}},
    )
    assert experiment_routes._live_sample_metadata({"sample_id": sample_id})[
        "heating_results"
    ] == {"ok": True}

    monkeypatch.setattr(experiment_routes, "_completed_sample_doc", lambda _id: None)
    assert experiment_routes._live_sample_metadata(
        {"sample_id": sample_id, "metadata": {"target": "as submitted"}}
    ) == {"target": "as submitted"}
