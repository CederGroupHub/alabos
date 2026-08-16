"""Helpers for building rich, debuggable error reports.

These reports are shown to operators on the Alab management dashboard and in Slack, and stored in the
logs. The goal is that whenever something goes wrong it is immediately obvious:

* **what** failed (exception type and message),
* **where** it failed (source file, line number and function), with the deepest frame inside this
  project's own code called out separately from third-party/standard-library frames, and
* **at which stage** of the process it failed (the last status message the task reported).

The full traceback is always appended at the bottom (starting with the standard
``Traceback (most recent call last):`` header) so that the existing Slack code-block formatting keeps
working and the complete stack is available for deep debugging.
"""

from __future__ import annotations

import sys
import traceback
from collections.abc import Iterable
from typing import Any

# Substrings identifying frames that belong to this project's own code (as opposed to third-party
# libraries or the standard library). Used to point operators at the most relevant source location.
_PROJECT_PATH_MARKERS = ("alab_one", "alab_management", "alab_control")

TRACEBACK_HEADER = "Traceback (most recent call last):"


def _extract_frames(tb) -> list[traceback.FrameSummary]:
    if tb is None:
        return []
    return list(traceback.extract_tb(tb))


def _is_project_frame(frame: traceback.FrameSummary) -> bool:
    filename = (frame.filename or "").replace("\\", "/").lower()
    return any(marker in filename for marker in _PROJECT_PATH_MARKERS)


def _short_path(filename: str | None) -> str:
    """Shorten an absolute path to something readable, anchored at the project root when possible."""
    if not filename:
        return "<unknown>"
    normalized = filename.replace("\\", "/")
    lowered = normalized.lower()
    for marker in _PROJECT_PATH_MARKERS:
        idx = lowered.rfind("/" + marker + "/")
        if idx != -1:
            return normalized[idx + 1 :]
    # Otherwise, keep just the file name and its parent directory.
    parts = normalized.rsplit("/", 2)
    return "/".join(parts[-2:]) if len(parts) >= 2 else normalized


def _format_frame(frame: traceback.FrameSummary | None) -> str:
    if frame is None:
        return "<unknown location>"
    return f"{_short_path(frame.filename)}:{frame.lineno} in {frame.name}()"


def get_error_origin(exc: BaseException | None = None) -> dict[str, Any]:
    """Return structured information about where an exception was raised.

    Args:
        exc: The exception to inspect. If ``None``, the exception currently being handled
            (``sys.exc_info()``) is used.

    Returns
    -------
        A dict with the exception type/message, the deepest frame (``raised_at``), and the deepest
        frame that belongs to this project's own code (``project_frame``), each rendered as a
        ``file:line in function()`` string.
    """
    if exc is None:
        exc_type, exc_value, tb = sys.exc_info()
    else:
        exc_type, exc_value, tb = type(exc), exc, exc.__traceback__

    frames = _extract_frames(tb)
    raised_at = frames[-1] if frames else None
    project_frame = next((f for f in reversed(frames) if _is_project_frame(f)), None)

    return {
        "exc_type": getattr(exc_type, "__name__", str(exc_type))
        if exc_type
        else "UnknownError",
        "exc_message": str(exc_value) if exc_value is not None else "",
        "raised_at": raised_at,
        "raised_at_str": _format_frame(raised_at),
        "project_frame": project_frame,
        "project_frame_str": _format_frame(project_frame) if project_frame else None,
    }


def _full_traceback(exc: BaseException | None) -> str:
    if exc is not None:
        return "".join(
            traceback.format_exception(type(exc), exc, exc.__traceback__)
        ).strip()
    return traceback.format_exc().strip()


def format_error_report(
    *,
    exc: BaseException | None = None,
    task_type: str | None = None,
    task_id: Any = None,
    samples: Iterable[str] | None = None,
    stage: str | None = None,
    header: str | None = None,
    include_traceback: bool = True,
) -> str:
    """Build a human-readable, debuggable error report.

    The report leads with a concise summary (what / where / stage / task / samples) and, when
    requested, appends the full traceback. It is safe to use the result as a dashboard message, a
    user-input prompt, or a Slack/email alert.

    Args:
        exc: The exception to report. If ``None``, the exception currently being handled is used.
        task_type: Name of the task class that failed.
        task_id: Identifier of the failing task.
        samples: Names of the samples involved.
        stage: The process stage where the failure happened (e.g. the task's last status message).
        header: A short title for the report (default ``"An error occurred"``).
        include_traceback: Whether to append the full traceback.
    """
    origin = get_error_origin(exc)

    lines: list[str] = []
    title = header or "An error occurred"
    if task_type:
        title = f"{title} in {task_type}"
    lines.append(f"ERROR: {title}")
    lines.append(f"- What:  {origin['exc_type']}: {origin['exc_message']}".rstrip())
    lines.append(f"- Where: {origin['raised_at_str']}")
    if (
        origin["project_frame_str"]
        and origin["project_frame_str"] != origin["raised_at_str"]
    ):
        lines.append(f"- In project code: {origin['project_frame_str']}")

    if stage:
        stage_text = str(stage).strip()
        # Use only the first line, and ignore stages that are themselves a stored traceback.
        if stage_text and TRACEBACK_HEADER not in stage_text:
            lines.append(f"- Stage: {stage_text.splitlines()[0]}")

    if task_type or task_id is not None:
        lines.append(f"- Task:  {task_type or '?'} (id: {task_id})")

    if samples:
        sample_list = ", ".join(str(s) for s in samples)
        if sample_list:
            lines.append(f"- Samples: {sample_list}")

    if include_traceback:
        tb_str = _full_traceback(exc)
        if tb_str and tb_str != "NoneType: None":
            lines.append("")
            lines.append(tb_str)

    return "\n".join(lines)
