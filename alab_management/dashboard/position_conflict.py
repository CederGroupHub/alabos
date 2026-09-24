"""User-input helpers when resource allocation is blocked by sample positions."""

from __future__ import annotations

from typing import Any

from bson import ObjectId

from alab_management.dashboard.lab_views import sample_view, user_input_view

CLEAR_POSITION_CONFLICT_ACTION = "clear_position_conflict"
CLEAR_POSITIONS_OPTION = "Clear conflicting position(s)"
UNBLOCK_POSITIONS_OPTION = "Unblock blocked position(s)"
KEEP_WAITING_OPTION = "Keep waiting"
_MAX_BLOCKERS_IN_PROMPT = 8


def _format_blocker(blocker: dict[str, Any]) -> str:
    position = blocker.get("position") or "?"
    reason = blocker.get("reason") or "UNKNOWN"
    if reason == "OCCUPIED":
        name = blocker.get("sample_name") or "unknown sample"
        sample_id = blocker.get("sample_id") or "?"
        return f"{position} occupied by {name} (id {sample_id})"
    if reason == "LOCKED":
        task_id = blocker.get("task_id") or "?"
        return f"{position} locked by task {task_id}"
    if reason == "BLOCKED":
        blocked_reason = blocker.get("blocked_reason")
        if blocked_reason:
            return f"{position} blocked ({blocked_reason})"
        return f"{position} blocked"
    return f"{position} ({reason})"


def _build_prompt(diagnosis: dict[str, Any]) -> str:
    shortages = diagnosis.get("shortages") or []
    has_blocked = bool(diagnosis.get("allow_unblock_blocked"))
    lines: list[str] = []
    if has_blocked:
        lines.append(
            "An automated experiment task is waiting for sample position(s) "
            "that are operator-blocked (or also occupied/locked)."
        )
    else:
        lines.append(
            "An automated experiment task is waiting for sample position(s) that "
            "are not free in software (leftover occupancy or a lock)."
        )

    for shortage in shortages:
        prefix = shortage.get("prefix") or "?"
        needed = shortage.get("needed", 1)
        available = shortage.get("available", 0)
        exact = shortage.get("exact", False)
        kind = "exact slot" if exact else "prefix"
        lines.append(
            f"- Needs {needed} at {kind} `{prefix}` "
            f"(available to this task: {available})."
        )
        blockers = shortage.get("blockers") or []
        for blocker in blockers[:_MAX_BLOCKERS_IN_PROMPT]:
            lines.append(f"  · {_format_blocker(blocker)}")
        remaining = len(blockers) - _MAX_BLOCKERS_IN_PROMPT
        if remaining > 0:
            lines.append(f"  · …and {remaining} more blocker(s).")

    if has_blocked:
        lines.append(
            "Unblock the blocked position(s) if they were blocked by mistake "
            "(for example an entire device), or keep waiting."
        )
    if diagnosis.get("allow_clear"):
        lines.append(
            "Clear the conflicting position(s) in software so the run can "
            "continue, or keep waiting."
        )
    elif not has_blocked:
        lines.append(
            "Use Sample Positions (per-slot Clear) or Lab Settings → Clear "
            "occupancy if the bench matches empty software state. "
            "This prompt will not bulk-clear a whole rack."
        )
    return "\n".join(lines)


def clear_position_conflict_blockers(blockers: list[dict[str, Any]]):
    """Clear occupancy and/or release locks for the listed blocker positions."""
    for blocker in blockers:
        position = blocker.get("position")
        if not position:
            continue
        reason = blocker.get("reason")
        sample_id = blocker.get("sample_id")
        if reason == "OCCUPIED" and sample_id:
            sample_view.move_sample(ObjectId(sample_id), None)
        # Always unlock after clear so a stale lock cannot re-block allocation.
        if (
            sample_view.get_sample_position(position) is not None
            and sample_view.is_locked_position(position)
        ):
            sample_view.release_sample_position(position)


def unblock_position_conflict_blockers(blockers: list[dict[str, Any]]):
    """Clear the operator ``blocked`` flag on listed positions (not occupancy)."""
    for blocker in blockers:
        position = blocker.get("position")
        if not position:
            continue
        try:
            sample_view.unblock_sample_position(position)
        except ValueError:
            # Locked-by-task: leave blocked; operator must release lock first.
            continue


def handle_position_conflict_user_input_response(
    request_doc: dict[str, Any], response: str
):
    context = request_doc.get("request_context") or {}
    if context.get("action") != CLEAR_POSITION_CONFLICT_ACTION:
        return
    if response == UNBLOCK_POSITIONS_OPTION:
        if not context.get("allow_unblock_blocked"):
            return
        unblock_position_conflict_blockers(context.get("blocked_blockers") or [])
        return
    if response != CLEAR_POSITIONS_OPTION:
        return
    if not context.get("allow_clear"):
        return
    clear_position_conflict_blockers(context.get("blockers") or [])


def ensure_position_conflict_user_input(
    *,
    task_id: ObjectId,
    resource_request_id: ObjectId,
    diagnosis: dict[str, Any],
):
    """Create a deduplicated user-input request for a position allocation stall."""
    shortages = diagnosis.get("shortages") or []
    if not shortages:
        return

    existing = user_input_view.get_pending_request_by_context(
        {
            "action": CLEAR_POSITION_CONFLICT_ACTION,
            "task_id": task_id,
            "resource_request_id": str(resource_request_id),
        }
    )
    if existing is not None:
        return

    allow_clear = bool(diagnosis.get("allow_clear"))
    allow_unblock_blocked = bool(diagnosis.get("allow_unblock_blocked"))
    options: list[str] = []
    if allow_unblock_blocked:
        options.append(UNBLOCK_POSITIONS_OPTION)
    if allow_clear:
        options.append(CLEAR_POSITIONS_OPTION)
    options.append(KEEP_WAITING_OPTION)

    user_input_view.insert_request(
        task_id=task_id,
        prompt=_build_prompt(diagnosis),
        options=options,
        category="Sample Positions",
        request_context_extra={
            "action": CLEAR_POSITION_CONFLICT_ACTION,
            "resource_request_id": str(resource_request_id),
            "allow_clear": allow_clear,
            "allow_unblock_blocked": allow_unblock_blocked,
            "blockers": (
                diagnosis.get("clearable_blockers") or []
                if allow_clear
                else []
            ),
            "blocked_blockers": (
                diagnosis.get("blocked_blockers") or []
                if allow_unblock_blocked
                else []
            ),
        },
    )
