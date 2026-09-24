"""Tests for collapsed sample-name reports used on the Data page."""

from datetime import datetime

from bson import ObjectId

from alab_management.dashboard.sample_report import (
    build_sample_report_row,
    canonical_sample_name,
    enrich_groups_with_historical_dosing,
    extract_actual_heating,
    powders_from_dosing,
    sample_has_dosing,
)


def test_canonical_sample_name_strips_numeric_replicates() -> None:
    assert canonical_sample_name("AppZr_66_1") == "AppZr_66"
    assert canonical_sample_name("AppZr_66_5") == "AppZr_66"
    assert canonical_sample_name("AppZr_66") == "AppZr_66"
    assert canonical_sample_name("AppZr_66BM") == "AppZr_66BM"
    assert canonical_sample_name("AppZr_57_OldAluminaCru") == "AppZr_57_OldAluminaCru"
    assert canonical_sample_name("Foo_12_3") == "Foo_12"


def test_extract_actual_heating_requires_a_run() -> None:
    assert extract_actual_heating({}) == {}
    assert extract_actual_heating({"heating_results": {}}) == {}
    got = extract_actual_heating(
        {
            "heating_results": {
                "heating_temperature": 1500,
                "heating_time": 720,
                "temperature_log": {"temperature_celsius": [1498, 1500]},
            }
        }
    )
    assert got["heating_done"] is True
    assert got["heating_temperature"] == 1500
    assert got["dwell_hours"] == 12


def test_powders_from_dosing_target_vs_actual() -> None:
    rows = powders_from_dosing(
        {
            "Powders": [
                {
                    "PowderName": "8YSZ",
                    "TargetMass": 0.80,
                    "Doses": [{"Mass": 0.41}, {"Mass": 0.40}],
                }
            ]
        }
    )
    assert rows[0]["powder_name"] == "8YSZ"
    assert rows[0]["target_mass"] == 0.80
    assert rows[0]["actual_mass"] == 0.81
    assert abs(rows[0]["delta_mass"] - 0.01) < 1e-9


def test_build_sample_report_row_collapses_aliases_and_tasks() -> None:
    sid_a = ObjectId()
    sid_b = ObjectId()
    task_id = ObjectId()
    samples = [
        {
            "_id": sid_a,
            "name": "AppZr_66_1",
            "created_at": datetime(2026, 7, 1),
            "metadata": {},
        },
        {
            "_id": sid_b,
            "name": "AppZr_66",
            "created_at": datetime(2026, 7, 2),
            "last_updated": datetime(2026, 7, 3),
            "metadata": {
                "target": "Zr0.8Fe0.2Ox",
                "powderdosing_results": {
                    "CrucibleSubRack": "SubRackA",
                    "CruciblePosition": 1,
                    "MixingPotPosition": 5,
                    "Powders": [
                        {
                            "PowderName": "Fe2O3",
                            "TargetMass": 0.1,
                            "Doses": [{"Mass": 0.11}],
                        }
                    ],
                },
            },
        },
    ]
    tasks = [
        {
            "_id": task_id,
            "type": "PowderDosing",
            "status": "COMPLETED",
            "created_at": datetime(2026, 7, 2),
            "samples": [{"sample_id": sid_b, "name": "AppZr_66"}],
        }
    ]
    row = build_sample_report_row("AppZr_66", samples, tasks)
    assert row["name"] == "AppZr_66"
    assert row["aliases"] == ["AppZr_66", "AppZr_66_1"]
    assert row["source_count"] == 2
    assert row["crucible"] == "A1"
    assert row["mixing_pot"] == 5
    assert row["powders"][0]["target_mass"] == 0.1
    assert row["powders"][0]["actual_mass"] == 0.11
    assert row["target_masses"] == "Fe2O3 0.1"
    assert row["actual_masses"] == "Fe2O3 0.11"
    assert row["related_tasks"][0]["type"] == "PowderDosing"
    assert "PowderDosing:COMPLETED" in row["task_summary"]


def test_enrich_groups_pulls_august_dosing_into_september_rerun() -> None:
    """Sept re-submit has empty metadata; August archived sample still has Labman dosing."""
    sept_id = ObjectId()
    aug_id = ObjectId()
    groups = {
        "AppZr_137": [
            {
                "_id": sept_id,
                "name": "AppZr_137",
                "created_at": datetime(2026, 9, 5),
                "metadata": {},
            }
        ]
    }
    historical = [
        {
            "_id": aug_id,
            "name": "AppZr_137",
            "created_at": datetime(2026, 8, 12),
            "metadata": {
                "powderdosing_results": {
                    "CrucibleSubRack": "SubRackA",
                    "CruciblePosition": 1,
                    "MixingPotPosition": 1,
                    "Powders": [
                        {
                            "PowderName": "Co3O4",
                            "TargetMass": 0.0128,
                            "Doses": [{"Mass": 0.01292}],
                        }
                    ],
                },
            },
        }
    ]
    assert not sample_has_dosing(groups["AppZr_137"][0])
    enrich_groups_with_historical_dosing(groups, historical)
    assert len(groups["AppZr_137"]) == 2
    row = build_sample_report_row("AppZr_137", groups["AppZr_137"], [])
    assert row["crucible"] == "A1"
    assert row["mixing_pot"] == 1
    assert row["powders"][0]["powder_name"] == "Co3O4"
    assert row["powders"][0]["actual_mass"] == 0.01292


def test_enrich_groups_skips_when_month_already_has_dosing() -> None:
    sid = ObjectId()
    groups = {
        "AppZr_137": [
            {
                "_id": sid,
                "name": "AppZr_137",
                "metadata": {
                    "powderdosing_results": {
                        "CruciblePosition": 2,
                        "CrucibleSubRack": "SubRackB",
                        "Powders": [{"PowderName": "CoO", "TargetMass": 1}],
                    }
                },
            }
        ]
    }
    enrich_groups_with_historical_dosing(
        groups,
        [
            {
                "_id": ObjectId(),
                "name": "AppZr_137",
                "metadata": {
                    "powderdosing_results": {
                        "CruciblePosition": 1,
                        "CrucibleSubRack": "SubRackA",
                        "Powders": [{"PowderName": "old", "TargetMass": 9}],
                    }
                },
            }
        ],
    )
    assert len(groups["AppZr_137"]) == 1
    assert groups["AppZr_137"][0]["_id"] == sid
