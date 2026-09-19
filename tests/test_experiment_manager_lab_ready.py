"""ExperimentManager holds PENDING work until lab devices are ready."""

from unittest.mock import MagicMock

from alab_management.experiment_manager import ExperimentManager


def test_handle_pending_experiments_holds_when_lab_not_ready(monkeypatch):
    manager = ExperimentManager.__new__(ExperimentManager)
    manager.experiment_view = MagicMock()
    manager.logger = MagicMock()
    manager._handle_pending_experiment = MagicMock()

    monkeypatch.setattr(
        "alab_management.device_rpc_status.get_lab_readiness",
        lambda: {
            "lab_ready": False,
            "lab_ready_label": "Lab starting...",
            "device_rpc": {"ready": False},
        },
    )
    ensure = MagicMock()
    monkeypatch.setattr(
        "alab_management.device_rpc_status.ensure_lab_starting_user_input",
        ensure,
    )

    manager.handle_pending_experiments()

    ensure.assert_called_once()
    manager.experiment_view.get_experiments_with_status.assert_not_called()
    manager._handle_pending_experiment.assert_not_called()


def test_handle_pending_experiments_runs_when_lab_ready(monkeypatch):
    manager = ExperimentManager.__new__(ExperimentManager)
    manager.experiment_view = MagicMock()
    manager.logger = MagicMock()
    manager._handle_pending_experiment = MagicMock()
    experiment = {"_id": "exp-1"}
    manager.experiment_view.get_experiments_with_status.return_value = [experiment]

    monkeypatch.setattr(
        "alab_management.device_rpc_status.get_lab_readiness",
        lambda: {
            "lab_ready": True,
            "lab_ready_label": "Lab ready",
            "device_rpc": {"ready": True},
        },
    )
    dismiss = MagicMock()
    monkeypatch.setattr(
        "alab_management.device_rpc_status.dismiss_lab_starting_user_input",
        dismiss,
    )

    manager.handle_pending_experiments()

    dismiss.assert_called_once()
    manager._handle_pending_experiment.assert_called_once_with(experiment=experiment)
