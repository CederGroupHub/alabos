"""Seed a small set of demo data into the working ALabOS database."""

from __future__ import annotations

from datetime import datetime, timedelta

from bson import ObjectId

from alab_management.experiment_view.experiment_view import ExperimentStatus, ExperimentView
from alab_management.sample_view import SampleView
from alab_management.task_view import TaskView
from alab_management.task_view.task_enums import TaskStatus

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

    now = datetime.now()

    samples = [
        {
            "_id": ObjectId(),
            "name": "DEMO_RACK_SAMPLE_A",
            "position": "DASH_input_rack/slot/1",
            "last_position": "DASH_input_rack/slot/1",
            "metadata": {
                "project": "demo",
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

    created_tasks = [
        {
            "_id": task_ids[0],
            "type": "Starting",
            "samples": [samples[0]],
            "parameters": {"start_position": "DASH_input_rack/slot/1"},
            "status": TaskStatus.COMPLETED,
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
            "samples": [samples[0], samples[1]],
            "parameters": {"demo_mode": True},
            "status": TaskStatus.COMPLETED,
            "message": "Demo powder dosing results are available for export.",
            "result": {
                "results_per_sample": {
                    samples[0]["name"]: samples[0]["metadata"]["powderdosing_results"],
                    samples[1]["name"]: samples[1]["metadata"]["powderdosing_results"],
                },
                "time_elapsed_seconds": 425.0,
            },
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
            "samples": [samples[1]],
            "parameters": {"label_vial": True},
            "status": TaskStatus.RUNNING,
            "message": "Demo ending task is still running so the dashboard shows mixed task states.",
            "result": {},
            "created_at": now - timedelta(minutes=7),
            "started_at": now - timedelta(minutes=6),
            "last_updated": now - timedelta(minutes=1),
            "tags": [DEMO_TAG],
            "prev_tasks": [task_ids[1]],
            "next_tasks": [],
        },
    ]

    task_view._task_collection.insert_many(created_tasks)

    experiment_view._experiment_collection.insert_many(
        [
            {
                "_id": ObjectId(),
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
                "_id": ObjectId(),
                "name": "DEMO_RUNNING_EXPERIMENT",
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
                "status": ExperimentStatus.RUNNING.name,
            },
        ]
    )

    return {
        "samples_created": len(samples),
        "tasks_created": len(created_tasks),
        "experiments_created": 2,
    }
