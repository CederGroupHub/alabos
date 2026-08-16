"""Seed a small set of demo data into the working ALabOS database."""

from __future__ import annotations

from datetime import datetime, timedelta

from bson import ObjectId

from alab_management.experiment_view.completed_experiment_view import (
    CompletedExperimentView,
)
from alab_management.experiment_view.experiment_view import ExperimentStatus, ExperimentView
from alab_management.sample_view import SampleView
from alab_management.task_view import TaskView
from alab_management.task_view.task_enums import TaskStatus
from alab_management.utils.data_objects import get_completed_collection

DEMO_TAG = "alabos_demo_seed"


def _demo_powder_results(transfer_mass: float, powder_mass: float, head_position: int):
    return {
        "ActualHeatDuration": 8111,
        "ActualTransferMass": transfer_mass,
        "CruciblePosition": 1,
        "CrucibleSubRack": "SubRackA",
        "DACDuration": 10,
        "DACSpeed": 2000,
        "EndReason": "Completed",
        "EthanolDispenseVolume": 15000,
        "MixingPotPosition": 1,
        "Powders": [
            {
                "PowderName": "Na2CO3",
                "TargetMass": round(powder_mass - 0.001, 6),
                "Doses": [
                    {
                        "HeadPosition": head_position,
                        "Mass": powder_mass,
                        "TimeStamp": "2026-08-16T09:15:00",
                    }
                ],
            }
        ],
        "TargetTransferVolume": 15000,
        "TransferTime": "2026-08-16T09:18:00",
    }


def _demo_powder_task_payload(samples: list[dict], powder_results: dict[str, dict]):
    return {
        "raw_results": {
            "IndexingRackQuadrant": 2,
            "Results": {
                "Rows": list(powder_results.values()),
                "WorkflowName": ObjectId(),
            },
        },
        "results_per_sample": powder_results,
        "mixingpot_to_sample": {
            str(result["MixingPotPosition"]): [sample_name]
            for sample_name, result in powder_results.items()
        },
        "time_elapsed_seconds": 425.0,
    }


def seed_demo_data(replace_existing: bool = True):
    """Seed demo samples, tasks, and experiments for dashboard testing.

    The inserted documents are tagged with ``alabos_demo_seed`` so they can be removed and recreated safely.
    """
    sample_view = SampleView()
    task_view = TaskView()
    experiment_view = ExperimentView()

    if replace_existing:
        sample_view._sample_collection.delete_many({"tags": DEMO_TAG})
        task_view._task_collection.delete_many({"tags": DEMO_TAG})
        experiment_view._experiment_collection.delete_many({"tags": DEMO_TAG})
        try:
            get_completed_collection("samples").delete_many({"tags": DEMO_TAG})
            get_completed_collection("tasks").delete_many({"tags": DEMO_TAG})
            get_completed_collection("experiment").delete_many({"tags": DEMO_TAG})
        except ValueError:
            pass

    now = datetime.now()

    samples = [
        {
            "_id": ObjectId(),
            "name": "DEMO_RACK_SAMPLE_A",
            "position": "DASH_input_rack/slot/1",
            "last_position": "DASH_input_rack/slot/1",
            "metadata": {
                "project": "demo",
                "target": "Na2TiTe3O12",
                "elements_present": ["Na", "Ti", "Te", "O"],
                "powderdosing_results": _demo_powder_results(
                    transfer_mass=8.6733,
                    powder_mass=0.12098,
                    head_position=5,
                ),
            },
            "tags": [DEMO_TAG],
        },
        {
            "_id": ObjectId(),
            "name": "DEMO_CONSUMABLE_SAMPLE_B",
            "position": "DASH_consumable_rack_A/vial_slot/3",
            "last_position": "DASH_consumable_rack_A/vial_slot/3",
            "metadata": {
                "project": "demo",
                "target": "Li0.57Ti0.28Ni0.15O0.98F0.02",
                "elements_present": ["Li", "Ti", "Ni", "O", "F"],
                "powderdosing_results": _demo_powder_results(
                    transfer_mass=7.2132,
                    powder_mass=1.35562,
                    head_position=13,
                ),
            },
            "tags": [DEMO_TAG],
        },
        {
            "_id": ObjectId(),
            "name": "DEMO_UNPLACED_SAMPLE_C",
            "position": None,
            "last_position": None,
            "metadata": {"project": "demo"},
            "tags": [DEMO_TAG],
        },
    ]

    for sample in samples:
        sample_view.create_sample(
            name=sample["name"],
            position=sample["position"],
            sample_id=sample["_id"],
            tags=sample["tags"],
            metadata=sample["metadata"],
        )

    task_ids = [ObjectId(), ObjectId(), ObjectId()]
    powder_results = {
        samples[0]["name"]: samples[0]["metadata"]["powderdosing_results"],
        samples[1]["name"]: samples[1]["metadata"]["powderdosing_results"],
    }

    created_tasks = [
        {
            "_id": task_ids[0],
            "type": "Starting",
            "samples": [samples[0]],
            "parameters": {"start_position": "DASH_input_rack/slot/1"},
            "status": TaskStatus.COMPLETED.name,
            "message": "Demo sample moved into the system successfully.",
            "result": {"demo": True, "action": "starting"},
            "created_at": now - timedelta(minutes=15),
            "started_at": now - timedelta(minutes=14),
            "completed_at": now - timedelta(minutes=13),
            "last_updated": now - timedelta(minutes=13),
            "tags": [DEMO_TAG],
            "prev_tasks": [],
            "next_tasks": [task_ids[1]],
        },
        {
            "_id": task_ids[1],
            "type": "PowderDosing",
            "samples": [
                {"name": samples[0]["name"], "sample_id": samples[0]["_id"]},
                {"name": samples[1]["name"], "sample_id": samples[1]["_id"]},
            ],
            "parameters": {
                "inputfiles": {
                    samples[0]["name"]: {
                        "CrucibleReplicates": 1,
                        "HeatingDuration": 8100,
                        "EthanolDispenseVolume": 15000,
                        "MinimumTransferMass": 8.0,
                        "MixerDuration": 10,
                        "MixerSpeed": 2000,
                        "PowderDispenses": [
                            {
                                "PowderName": "Na2CO3",
                                "TargetMass": powder_results[samples[0]["name"]]["Powders"][0]["TargetMass"],
                            }
                        ],
                        "TargetTransferVolume": 15000,
                        "time_added": "2026-08-16T09:10:00",
                    },
                    samples[1]["name"]: {
                        "CrucibleReplicates": 1,
                        "HeatingDuration": 8100,
                        "EthanolDispenseVolume": 15000,
                        "MinimumTransferMass": 7.0,
                        "MixerDuration": 10,
                        "MixerSpeed": 2000,
                        "PowderDispenses": [
                            {
                                "PowderName": "Na2CO3",
                                "TargetMass": powder_results[samples[1]["name"]]["Powders"][0]["TargetMass"],
                            }
                        ],
                        "TargetTransferVolume": 15000,
                        "time_added": "2026-08-16T09:11:00",
                    },
                }
            },
            "status": TaskStatus.COMPLETED.name,
            "message": "Demo powder dosing results are available for export.",
            "task_actor_id": "demo-powder-dosing-actor",
            "result": _demo_powder_task_payload(samples, powder_results),
            "created_at": now - timedelta(minutes=12),
            "started_at": now - timedelta(minutes=11),
            "completed_at": now - timedelta(minutes=8),
            "last_updated": now - timedelta(minutes=8),
            "tags": [DEMO_TAG],
            "prev_tasks": [task_ids[0]],
            "next_tasks": [task_ids[2]],
        },
        {
            "_id": task_ids[2],
            "type": "Ending",
            "samples": [
                {"name": samples[1]["name"], "sample_id": samples[1]["_id"]},
            ],
            "parameters": {},
            "status": TaskStatus.COMPLETED.name,
            "message": f"Sample {samples[1]['name']} has been removed. Skipped.",
            "task_actor_id": "demo-ending-actor",
            "created_at": now - timedelta(minutes=7),
            "started_at": now - timedelta(minutes=6),
            "completed_at": now - timedelta(minutes=1),
            "last_updated": now - timedelta(minutes=1),
            "tags": [DEMO_TAG],
            "prev_tasks": [task_ids[1]],
            "next_tasks": [],
        },
    ]

    task_view._task_collection.insert_many(created_tasks)

    experiment_ids = [ObjectId(), ObjectId()]
    seeded_experiments = [
            {
                "_id": experiment_ids[0],
                "name": "DEMO_COMPLETED_EXPERIMENT",
                "samples": [
                    {
                        "name": samples[0]["name"],
                        "sample_id": samples[0]["_id"],
                        "metadata": samples[0]["metadata"],
                        "tags": samples[0]["tags"],
                    },
                    {
                        "name": samples[1]["name"],
                        "sample_id": samples[1]["_id"],
                        "metadata": samples[1]["metadata"],
                        "tags": samples[1]["tags"],
                    },
                ],
                "tasks": [
                    {
                        "type": "Starting",
                        "task_id": task_ids[0],
                        "parameters": {"start_position": "DASH_input_rack/slot/1"},
                    },
                    {
                        "type": "PowderDosing",
                        "task_id": task_ids[1],
                        "parameters": {"demo_mode": True},
                    },
                ],
                "tags": [DEMO_TAG],
                "metadata": {"demo_seed": True},
                "submitted_at": now - timedelta(minutes=16),
                "completed_at": now - timedelta(minutes=8),
                "status": ExperimentStatus.COMPLETED.name,
            },
            {
                "_id": experiment_ids[1],
                "name": "DEMO_SECOND_COMPLETED_EXPERIMENT",
                "samples": [
                    {
                        "name": samples[1]["name"],
                        "sample_id": samples[1]["_id"],
                        "metadata": samples[1]["metadata"],
                        "tags": samples[1]["tags"],
                    },
                    {
                        "name": samples[2]["name"],
                        "sample_id": samples[2]["_id"],
                        "metadata": samples[2]["metadata"],
                        "tags": samples[2]["tags"],
                    },
                ],
                "tasks": [
                    {
                        "type": "PowderDosing",
                        "task_id": task_ids[1],
                        "parameters": {"demo_mode": True},
                    },
                    {
                        "type": "Ending",
                        "task_id": task_ids[2],
                        "parameters": {"label_vial": True},
                    },
                ],
                "tags": [DEMO_TAG],
                "metadata": {"demo_seed": True},
                "submitted_at": now - timedelta(minutes=7),
                "completed_at": now - timedelta(minutes=1),
                "status": ExperimentStatus.COMPLETED.name,
            },
        ]
    experiment_view._experiment_collection.insert_many(seeded_experiments)

    try:
        completed_view = CompletedExperimentView()
        for experiment_id in experiment_ids:
            completed_view.save_experiment(experiment_id)
    except ValueError:
        pass

    # Match the production-like split more closely by leaving historical
    # experiment/task records in the completed DB only.
    task_view._task_collection.delete_many({"tags": DEMO_TAG})
    experiment_view._experiment_collection.delete_many({"tags": DEMO_TAG})

    return {
        "samples_created": len(samples),
        "tasks_created": len(created_tasks),
        "experiments_created": 2,
    }
