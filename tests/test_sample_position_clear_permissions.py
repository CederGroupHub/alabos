"""Per-slot Clear gating based on live experiment ownership."""

from alab_management.dashboard.routes.sample_positions import (
    _apply_clear_permissions,
    _experiment_is_live,
    clear_blocked_reason_for_experiment,
)


def test_experiment_is_live_only_for_nonterminal_live_db_docs():
    assert _experiment_is_live("RUNNING", from_live_db=True) is True
    assert _experiment_is_live("PENDING", from_live_db=True) is True
    assert _experiment_is_live("ERROR", from_live_db=True) is True
    assert _experiment_is_live("COMPLETED", from_live_db=True) is False
    assert _experiment_is_live("CANCELLED", from_live_db=True) is False
    assert _experiment_is_live("RUNNING", from_live_db=False) is False
    assert _experiment_is_live("COMPLETED", from_live_db=False) is False


def test_clear_blocked_reason_only_when_live():
    assert (
        clear_blocked_reason_for_experiment(
            experiment_live=False,
            experiment_name="done",
            experiment_status="COMPLETED",
        )
        is None
    )
    reason = clear_blocked_reason_for_experiment(
        experiment_live=True,
        experiment_name="Nov6_test",
        experiment_status="RUNNING",
    )
    assert reason is not None
    assert "live experiment" in reason
    assert "Nov6_test" in reason
    assert "RUNNING" in reason


def test_apply_clear_permissions_per_slot():
    racks = [
        {
            "slot_groups": {
                "slot": [
                    {
                        "name": "DASH_input_rack/slot/1",
                        "sample": {
                            "name": "live_sample",
                            "experiment_live": True,
                            "experiment_name": "A",
                            "experiment_status": "RUNNING",
                        },
                    },
                    {
                        "name": "DASH_input_rack/slot/2",
                        "sample": {
                            "name": "finished_sample",
                            "experiment_live": False,
                            "experiment_name": "B",
                            "experiment_status": "CANCELLED",
                        },
                    },
                    {
                        "name": "DASH_input_rack/slot/3",
                        "sample": None,
                    },
                ]
            }
        }
    ]
    _apply_clear_permissions(racks)
    slots = racks[0]["slot_groups"]["slot"]
    assert slots[0]["clear_allowed"] is False
    assert "live experiment" in slots[0]["clear_blocked_reason"]
    assert slots[1]["clear_allowed"] is True
    assert slots[1]["clear_blocked_reason"] is None
    assert slots[2]["clear_allowed"] is False
    assert slots[2]["clear_blocked_reason"] is None
