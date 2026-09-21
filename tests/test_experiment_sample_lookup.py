"""Experiment GET must tolerate samples pruned from live into completed."""

from types import SimpleNamespace
from unittest.mock import MagicMock

from bson import ObjectId

from alab_management.dashboard.routes import experiment as experiment_routes


def test_sample_payload_uses_live_sample(monkeypatch):
    sample_id = ObjectId()
    monkeypatch.setattr(
        experiment_routes,
        "sample_view",
        SimpleNamespace(
            get_sample=lambda sid: SimpleNamespace(
                name="S1",
                position="DASH_input_rack/slot/1",
                last_position="DASH_input_rack/slot/1",
            )
        ),
    )
    payload = experiment_routes._sample_payload_for_experiment(
        {"name": "S1", "sample_id": sample_id}
    )
    assert payload["position"] == "DASH_input_rack/slot/1"
    assert payload["id"] == str(sample_id)


def test_sample_payload_falls_back_to_completed(monkeypatch):
    sample_id = ObjectId()

    def boom(_sid):
        raise ValueError(f"No sample found with id: {_sid}")

    monkeypatch.setattr(
        experiment_routes,
        "sample_view",
        SimpleNamespace(get_sample=boom),
    )
    monkeypatch.setattr(
        experiment_routes,
        "_completed_sample_doc",
        lambda sid: {
            "_id": sid,
            "name": "Archived",
            "position": None,
            "last_position": "MOBILE_arm_ALFRED/SubRackA/1",
        },
    )
    payload = experiment_routes._sample_payload_for_experiment(
        {"name": "S1", "sample_id": sample_id}
    )
    assert payload["name"] == "Archived"
    assert payload["position"] == "MOBILE_arm_ALFRED/SubRackA/1"
    assert payload["last_position"] == "MOBILE_arm_ALFRED/SubRackA/1"


def test_sample_payload_survives_missing_everywhere(monkeypatch):
    sample_id = ObjectId()
    monkeypatch.setattr(
        experiment_routes,
        "sample_view",
        SimpleNamespace(
            get_sample=MagicMock(side_effect=ValueError("missing")),
        ),
    )
    monkeypatch.setattr(experiment_routes, "_completed_sample_doc", lambda sid: None)
    payload = experiment_routes._sample_payload_for_experiment(
        {"name": "Orphan", "sample_id": sample_id}
    )
    assert payload["name"] == "Orphan"
    assert payload["position"] is None
    assert payload["id"] == str(sample_id)
