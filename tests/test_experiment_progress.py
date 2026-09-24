"""Tests for experiment progress_steps (previous / current / next)."""

from datetime import datetime, timedelta

from bson import ObjectId

from alab_management.dashboard.experiment_progress import (
    build_task_description,
    compute_progress_steps,
    humanize_task_type,
    short_operator_message,
    summarize_task,
)
from alab_management.task_view.wait_messages import WORKER_QUEUE_MESSAGE, default_wait_message
from alab_management.utils.error_context import TRACEBACK_HEADER


def _task(
    *,
    type_: str,
    status: str,
    samples: list[str] | None = None,
    message: str = "",
    prev: list[ObjectId] | None = None,
    completed_at: datetime | None = None,
    started_at: datetime | None = None,
    oid: ObjectId | None = None,
) -> dict:
    doc = {
        "_id": oid or ObjectId(),
        "type": type_,
        "status": status,
        "message": message,
        "samples": [{"name": name, "sample_id": ObjectId()} for name in (samples or [])],
        "prev_tasks": list(prev or []),
        "next_tasks": [],
    }
    if completed_at is not None:
        doc["completed_at"] = completed_at
    if started_at is not None:
        doc["started_at"] = started_at
    return doc


def test_humanize_task_type() -> None:
    assert humanize_task_type("RecoverPowder") == "Recover powder"
    assert humanize_task_type("Heating") == "Heating"


def test_summarize_task_explains_initiated_when_message_empty() -> None:
    task = _task(type_="Heating", status="INITIATED", samples=["A"])
    summary = summarize_task(task)
    assert summary["message"] == WORKER_QUEUE_MESSAGE
    assert WORKER_QUEUE_MESSAGE in summary["description"]


def test_summarize_task_keeps_existing_message() -> None:
    task = _task(
        type_="Heating",
        status="INITIATED",
        samples=["A"],
        message="custom note",
    )
    summary = summarize_task(task)
    assert summary["message"] == "custom note"
    assert "custom note" in summary["description"]


def test_default_wait_message_covers_idle_statuses() -> None:
    assert "previous task" in default_wait_message("WAITING")
    assert "worker queue" in default_wait_message("READY")
    assert default_wait_message("RUNNING") == ""
    assert default_wait_message("RUNNING", "ramping") == "ramping"


def test_short_operator_message_strips_traceback() -> None:
    message = (
        "ERROR: Task failed in Moving\n"
        "- What: RuntimeError\n"
        "    Error in thread for sample 'S1'\n"
        "- Cause: RuntimeError\n"
        "    delivery request was cancelled\n"
        f"\n{TRACEBACK_HEADER}\n"
        "File moving.py, line 627\n"
    )
    assert short_operator_message(message) == "delivery request was cancelled"
    description = build_task_description(
        _task(type_="Moving", status="ERROR", samples=["S1"], message=message)
    )
    assert description == "Moving — S1 — delivery request was cancelled"
    assert TRACEBACK_HEADER not in description


def test_build_task_description_includes_samples_and_message() -> None:
    task = _task(
        type_="RecoverPowder",
        status="RUNNING",
        samples=["S1", "S2"],
        message="shaking vial",
    )
    assert (
        build_task_description(task)
        == "Recover powder — S1, S2 — shaking vial"
    )


def test_linear_chain_previous_current_next() -> None:
    t0 = ObjectId()
    t1 = ObjectId()
    t2 = ObjectId()
    now = datetime(2026, 9, 17, 12, 0, 0)
    tasks = [
        _task(
            oid=t0,
            type_="Dispense",
            status="COMPLETED",
            samples=["A"],
            completed_at=now - timedelta(minutes=10),
        ),
        _task(
            oid=t1,
            type_="Heating",
            status="RUNNING",
            samples=["A"],
            message="ramping",
            prev=[t0],
            started_at=now - timedelta(minutes=2),
        ),
        _task(
            oid=t2,
            type_="Diffraction",
            status="WAITING",
            samples=["A"],
            prev=[t1],
        ),
    ]
    steps = compute_progress_steps(tasks)
    assert [s["id"] for s in steps["previous"]] == [str(t0)]
    assert [s["id"] for s in steps["current"]] == [str(t1)]
    assert steps["current"][0]["description"].startswith("Heating — A")
    assert steps["next"] == []  # waiting on t1, not yet unblocked


def test_fan_out_two_ready_nexts() -> None:
    t0 = ObjectId()
    t1 = ObjectId()
    t2 = ObjectId()
    now = datetime(2026, 9, 17, 12, 0, 0)
    tasks = [
        _task(
            oid=t0,
            type_="Prep",
            status="COMPLETED",
            completed_at=now,
        ),
        _task(oid=t1, type_="PathA", status="READY", prev=[t0]),
        _task(oid=t2, type_="PathB", status="READY", prev=[t0]),
    ]
    steps = compute_progress_steps(tasks)
    assert [s["id"] for s in steps["previous"]] == [str(t0)]
    assert steps["current"] == []
    assert [s["id"] for s in steps["next"]] == [str(t1), str(t2)]


def test_waiting_unblocked_counts_as_next() -> None:
    t0 = ObjectId()
    t1 = ObjectId()
    now = datetime(2026, 9, 17, 12, 0, 0)
    tasks = [
        _task(oid=t0, type_="A", status="COMPLETED", completed_at=now),
        _task(oid=t1, type_="B", status="WAITING", prev=[t0]),
    ]
    steps = compute_progress_steps(tasks)
    assert [s["id"] for s in steps["next"]] == [str(t1)]


def test_all_completed_previous_is_latest() -> None:
    t0 = ObjectId()
    t1 = ObjectId()
    t2 = ObjectId()
    base = datetime(2026, 9, 17, 10, 0, 0)
    tasks = [
        _task(
            oid=t0,
            type_="A",
            status="COMPLETED",
            completed_at=base,
        ),
        _task(
            oid=t1,
            type_="B",
            status="COMPLETED",
            completed_at=base + timedelta(hours=1),
            prev=[t0],
        ),
        _task(
            oid=t2,
            type_="C",
            status="COMPLETED",
            completed_at=base + timedelta(hours=2),
            prev=[t1],
        ),
    ]
    steps = compute_progress_steps(tasks)
    assert [s["id"] for s in steps["previous"]] == [str(t2)]
    assert steps["current"] == []
    assert steps["next"] == []


def test_cancelled_mid_run_previous_from_completed_feeder() -> None:
    t0 = ObjectId()
    t1 = ObjectId()
    t2 = ObjectId()
    now = datetime(2026, 9, 17, 12, 0, 0)
    tasks = [
        _task(
            oid=t0,
            type_="A",
            status="COMPLETED",
            completed_at=now - timedelta(minutes=5),
        ),
        _task(
            oid=t1,
            type_="B",
            status="CANCELLED",
            prev=[t0],
            completed_at=now,
        ),
        _task(oid=t2, type_="C", status="CANCELLED", prev=[t1]),
    ]
    steps = compute_progress_steps(tasks)
    assert steps["current"] == []
    assert [s["id"] for s in steps["previous"]] == [str(t0)]
    assert steps["next"] == []
