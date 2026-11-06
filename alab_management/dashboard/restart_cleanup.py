"""Complete non-blocking restart cleanup when the operator OKs the dashboard prompt."""

from __future__ import annotations

import logging
from typing import Any

from bson import ObjectId

from alab_management.lab_view import LabView
from alab_management.task_view import TaskView
from alab_management.task_view.task_enums import TaskStatus

cli_logger = logging.getLogger(__name__)

OK_RESPONSE = "OK"


def handle_restart_cleanup_user_input_response(
    request_doc: dict[str, Any], response: str
) -> None:
    """On OK of a restart-cleanup request: release locks, optionally clear positions, cancel task.

    Stacked duplicates that were superseded must not run this path — only the live OK does.
    """
    context = request_doc.get("request_context") or {}
    if not context.get("restart_cleanup"):
        return
    # Superseded / non-OK responses must not release locks.
    if response != OK_RESPONSE:
        return

    task_id_raw = context.get("task_id")
    if task_id_raw is None:
        cli_logger.error(
            "restart_cleanup request %s missing task_id; ignoring",
            request_doc.get("_id"),
        )
        return

    task_id = ObjectId(task_id_raw)
    clear_positions = bool(context.get("clear_positions", True))
    sample_id_strs = context.get("sample_ids") or []

    lab_view = LabView(task_id=task_id)
    samples = None
    if sample_id_strs:
        wanted = {ObjectId(sid) for sid in sample_id_strs}
        samples = [
            entry
            for entry in lab_view._LabView__task_entry["samples"]
            if entry["sample_id"] in wanted
        ]

    lab_view.finish_cleanup_after_ack(
        clear_positions=clear_positions,
        samples=samples,
    )
    TaskView().update_status(task_id=task_id, status=TaskStatus.CANCELLED)
    cli_logger.info(
        "Restart cleanup completed for task %s (clear_positions=%s).",
        task_id,
        clear_positions,
    )
