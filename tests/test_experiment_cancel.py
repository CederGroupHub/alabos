"""Tests for per-experiment Cancel."""

from concurrent.futures import Future
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from bson import ObjectId

from alab_management.experiment_cancel import cancel_experiment_software_state
from alab_management.experiment_view.experiment_view import dashboard_experiment_status
from alab_management.resource_manager.resource_requester import ResourceRequester
from alab_management.task_view.task import TaskCancelledError
from alab_management.user_input import CANCEL_RESPONSE, UserInputView, UserRequestStatus


def test_cancel_experiment_force_cancels_live_tasks_and_closes(monkeypatch):
    exp_id = ObjectId()
    waiting_task_id = ObjectId()
    running_task_id = ObjectId()
    experiment = {
        "_id": exp_id,
        "status": "RUNNING",
        "tasks": [
            {"task_id": waiting_task_id},
            {"task_id": running_task_id},
        ],
    }
    live_tasks = [
        {"_id": waiting_task_id, "task_actor_id": None},
        {"_id": running_task_id, "task_actor_id": "msg-1"},
    ]

    task_collection = MagicMock()
    task_collection.find.return_value = live_tasks
    task_view = MagicMock()
    task_view._task_collection = task_collection

    experiment_view = MagicMock()
    experiment_view.get_experiment.return_value = experiment

    user_input_view = MagicMock()
    user_input_view.dismiss_pending_requests.return_value = 1

    device_collection = MagicMock()
    device_collection.update_many.return_value.modified_count = 2
    sample_positions = MagicMock()
    sample_positions.update_many.return_value.modified_count = 2
    requests = MagicMock()
    requests.update_many.return_value.modified_count = 3

    monkeypatch.setattr("alab_management.experiment_cancel.TaskView", lambda: task_view)
    monkeypatch.setattr(
        "alab_management.experiment_cancel.ExperimentView", lambda: experiment_view
    )
    monkeypatch.setattr(
        "alab_management.experiment_cancel.DeviceView",
        lambda: SimpleNamespace(_device_collection=device_collection),
    )
    monkeypatch.setattr(
        "alab_management.experiment_cancel.SampleView",
        lambda: SimpleNamespace(_sample_positions_collection=sample_positions),
    )
    monkeypatch.setattr(
        "alab_management.experiment_cancel.UserInputView", lambda: user_input_view
    )
    monkeypatch.setattr(
        "alab_management.experiment_cancel.get_collection", lambda name: requests
    )
    abort = MagicMock()
    monkeypatch.setattr("alab_management.experiment_cancel._abort_task_actor", abort)

    summary = cancel_experiment_software_state(exp_id)

    assert summary["tasks_cancelled"] == 2
    assert summary["user_inputs_dismissed"] == 1
    assert summary["resource_requests_cancelled"] == 3
    assert summary["devices_released"] == 2
    assert summary["positions_unlocked"] == 2
    assert summary["experiment_closed"] is True
    experiment_view.update_experiment_status.assert_called_once()
    user_input_view.dismiss_pending_requests.assert_called_once()
    assert user_input_view.dismiss_pending_requests.call_args.kwargs["experiment_id"] == exp_id
    device_collection.update_many.assert_called_once()
    assert device_collection.update_many.call_args.args[0]["task_id"]["$in"] == [
        waiting_task_id,
        running_task_id,
    ]
    assert abort.call_count == 2
    task_collection.update_many.assert_called_once()


def test_cancel_experiment_closes_when_every_task_is_terminal(monkeypatch):
    exp_id = ObjectId()
    task_id = ObjectId()
    experiment = {
        "_id": exp_id,
        "status": "RUNNING",
        "tasks": [{"task_id": task_id}],
    }

    task_collection = MagicMock()
    task_collection.find.return_value = [{"_id": task_id, "task_actor_id": None}]
    task_view = MagicMock()
    task_view._task_collection = task_collection

    experiment_view = MagicMock()
    experiment_view.get_experiment.return_value = experiment

    monkeypatch.setattr("alab_management.experiment_cancel.TaskView", lambda: task_view)
    monkeypatch.setattr(
        "alab_management.experiment_cancel.ExperimentView", lambda: experiment_view
    )
    monkeypatch.setattr(
        "alab_management.experiment_cancel.DeviceView",
        lambda: SimpleNamespace(_device_collection=MagicMock()),
    )
    monkeypatch.setattr(
        "alab_management.experiment_cancel.SampleView",
        lambda: SimpleNamespace(_sample_positions_collection=MagicMock()),
    )
    monkeypatch.setattr(
        "alab_management.experiment_cancel.UserInputView",
        lambda: SimpleNamespace(dismiss_pending_requests=lambda **kwargs: 0),
    )
    monkeypatch.setattr(
        "alab_management.experiment_cancel.get_collection",
        lambda name: SimpleNamespace(update_many=lambda *args, **kwargs: SimpleNamespace(modified_count=0)),
    )
    monkeypatch.setattr("alab_management.experiment_cancel._abort_task_actor", MagicMock())

    summary = cancel_experiment_software_state(exp_id)

    assert summary["experiment_closed"] is True
    experiment_view.update_experiment_status.assert_called_once()


def test_cancel_pending_experiment_without_task_ids(monkeypatch):
    exp_id = ObjectId()
    experiment = {"_id": exp_id, "status": "PENDING", "tasks": [{"task_id": None}]}

    experiment_view = MagicMock()
    experiment_view.get_experiment.return_value = experiment

    monkeypatch.setattr("alab_management.experiment_cancel.TaskView", lambda: MagicMock())
    monkeypatch.setattr(
        "alab_management.experiment_cancel.ExperimentView", lambda: experiment_view
    )
    monkeypatch.setattr(
        "alab_management.experiment_cancel.DeviceView",
        lambda: SimpleNamespace(_device_collection=MagicMock()),
    )
    monkeypatch.setattr(
        "alab_management.experiment_cancel.SampleView",
        lambda: SimpleNamespace(_sample_positions_collection=MagicMock()),
    )
    monkeypatch.setattr(
        "alab_management.experiment_cancel.UserInputView",
        lambda: SimpleNamespace(dismiss_pending_requests=lambda **kwargs: 0),
    )
    monkeypatch.setattr(
        "alab_management.experiment_cancel.get_collection",
        lambda name: SimpleNamespace(update_many=lambda *args, **kwargs: SimpleNamespace(modified_count=0)),
    )

    summary = cancel_experiment_software_state(exp_id)

    assert summary["tasks_cancelled"] == 0
    assert summary["experiment_closed"] is True


def test_cancel_missing_experiment_raises(monkeypatch):
    experiment_view = MagicMock()
    experiment_view.get_experiment.return_value = None
    monkeypatch.setattr("alab_management.experiment_cancel.TaskView", lambda: MagicMock())
    monkeypatch.setattr(
        "alab_management.experiment_cancel.ExperimentView", lambda: experiment_view
    )
    monkeypatch.setattr(
        "alab_management.experiment_cancel.DeviceView", lambda: MagicMock()
    )
    monkeypatch.setattr(
        "alab_management.experiment_cancel.SampleView", lambda: MagicMock()
    )
    monkeypatch.setattr(
        "alab_management.experiment_cancel.UserInputView", lambda: MagicMock()
    )

    with pytest.raises(ValueError, match="Experiment not found"):
        cancel_experiment_software_state(ObjectId())


def test_retrieve_user_input_raises_when_task_is_cancelling():
    request_id = ObjectId()
    task_id = ObjectId()
    request = {
        "_id": request_id,
        "status": UserRequestStatus.PENDING.value,
        "request_context": {"task_id": task_id},
        "response": None,
        "note": "",
    }
    view = UserInputView.__new__(UserInputView)
    view._input_collection = MagicMock()
    view._task_view = MagicMock()
    view._task_view.is_canceling.return_value = True
    view.get_request = lambda _request_id: request
    view.update_request_status = MagicMock()

    with pytest.raises(TaskCancelledError, match="user input"):
        view.retrieve_user_input(request_id)

    view.update_request_status.assert_called_once()
    assert view.update_request_status.call_args.kwargs["response"] == CANCEL_RESPONSE


def test_retrieve_user_input_returns_response_when_not_cancelling():
    request_id = ObjectId()
    request = {
        "_id": request_id,
        "status": UserRequestStatus.FULLFILLED.value,
        "request_context": {"task_id": ObjectId()},
        "response": "OK",
        "note": "",
    }
    view = UserInputView.__new__(UserInputView)
    view._task_view = MagicMock()
    view._task_view.is_canceling.return_value = False
    view.get_request = lambda _request_id: request

    assert view.retrieve_user_input(request_id) == "OK"


def _requester_without_thread():
    requester = ResourceRequester.__new__(ResourceRequester)
    requester.task_id = ObjectId()
    requester._stop = True
    requester._thread = SimpleNamespace(join=lambda: None)
    return requester


def test_get_concurrent_result_raises_when_task_is_cancelling(monkeypatch):
    requester = _requester_without_thread()
    future = Future()
    task_view = MagicMock()
    task_view.is_canceling.return_value = True
    monkeypatch.setattr(
        "alab_management.task_view.task_view.TaskView", lambda: task_view
    )

    with pytest.raises(TaskCancelledError, match="resources"):
        requester.get_concurrent_result(future, timeout=2)


def test_get_concurrent_result_returns_when_fulfilled(monkeypatch):
    requester = _requester_without_thread()
    future = Future()
    future.set_result({"devices": {}, "request_id": ObjectId()})
    task_view = MagicMock()
    task_view.is_canceling.return_value = False
    monkeypatch.setattr(
        "alab_management.task_view.task_view.TaskView", lambda: task_view
    )

    assert requester.get_concurrent_result(future)["devices"] == {}


def test_dashboard_status_shows_cancelled_when_nothing_is_live():
    assert (
        dashboard_experiment_status(
            ["ERROR", "CANCELLED", "CANCELLED"], "COMPLETED"
        )
        == "CANCELLED"
    )
    assert dashboard_experiment_status(["COMPLETED", "COMPLETED"], "COMPLETED") == "COMPLETED"
    assert dashboard_experiment_status(["ERROR", "ERROR"], "COMPLETED") == "ERROR"
    assert dashboard_experiment_status(["RUNNING", "ERROR"], "RUNNING") == "ERROR"
    assert dashboard_experiment_status(["RUNNING", "WAITING"], "RUNNING") == "RUNNING"
