"""Service launch logs for the AlabOS dashboard Logs view.

The restart launcher sets ``ALABOS_LAUNCH_LOG_DIR`` to the per-launch folder containing
``lab.log``, ``alabos_launch.log``, ``alabos_worker.log``, and ``alab_one_launch.log``.
"""

from __future__ import annotations

import os
from pathlib import Path

from alab_management.utils.device_verbose_logging import (
    DEFAULT_VERBOSE_LOG_TAIL,
    MAX_VERBOSE_LOG_TAIL,
    _tail_text_lines,
)

ALABOS_LAUNCH_LOG_DIR_ENV = "ALABOS_LAUNCH_LOG_DIR"

LAUNCH_LOG_SOURCES: tuple[dict[str, str], ...] = (
    {"id": "lab", "title": "Lab", "filename": "lab.log"},
    {"id": "alabos_launch", "title": "alabos launch", "filename": "alabos_launch.log"},
    {"id": "alabos_worker", "title": "alabos worker", "filename": "alabos_worker.log"},
    {
        "id": "alab_one_dashboard",
        "title": "alab_one dashboard",
        "filename": "alab_one_launch.log",
    },
)

_SOURCES_BY_ID = {item["id"]: item for item in LAUNCH_LOG_SOURCES}


def get_launch_log_dir() -> Path | None:
    """Return the current launch log directory, or None if unset."""
    raw = os.getenv(ALABOS_LAUNCH_LOG_DIR_ENV, "").strip()
    if not raw:
        return None
    return Path(raw)


def list_launch_log_sources() -> list[dict]:
    """Describe each Logs tab and whether its file exists yet."""
    log_dir = get_launch_log_dir()
    sources: list[dict] = []
    for item in LAUNCH_LOG_SOURCES:
        available = False
        if log_dir is not None:
            available = (log_dir / item["filename"]).is_file()
        sources.append(
            {
                "id": item["id"],
                "title": item["title"],
                "filename": item["filename"],
                "available": available,
                "log_dir_configured": log_dir is not None,
            }
        )
    return sources


def read_launch_log_tail(source_id: str, max_lines: int = DEFAULT_VERBOSE_LOG_TAIL) -> dict:
    """Return trailing lines for a sandboxed launch-log source id."""
    if source_id not in _SOURCES_BY_ID:
        raise ValueError(f"Unknown log source: {source_id!r}")
    if max_lines < 1:
        max_lines = 1
    if max_lines > MAX_VERBOSE_LOG_TAIL:
        max_lines = MAX_VERBOSE_LOG_TAIL

    log_dir = get_launch_log_dir()
    if log_dir is None:
        return {
            "available": False,
            "reason": "no_launch_dir",
            "lines": [],
            "source_id": source_id,
            "title": _SOURCES_BY_ID[source_id]["title"],
        }

    filename = _SOURCES_BY_ID[source_id]["filename"]
    log_path = (log_dir / filename).resolve()
    try:
        log_path.relative_to(log_dir.resolve())
    except ValueError as exc:
        raise ValueError(f"Invalid log path for source {source_id!r}") from exc

    if not log_path.is_file():
        return {
            "available": False,
            "reason": "no_file",
            "lines": [],
            "source_id": source_id,
            "title": _SOURCES_BY_ID[source_id]["title"],
        }

    return {
        "available": True,
        "reason": None,
        "lines": _tail_text_lines(log_path, max_lines),
        "source_id": source_id,
        "title": _SOURCES_BY_ID[source_id]["title"],
    }
