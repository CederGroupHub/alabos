"""Per-device verbose logging to files for the restart launcher."""

from __future__ import annotations

import os
from datetime import datetime
from pathlib import Path

MOBILE_ROBOT_DEVICE_NAME = "MOBILE_arm_ALFRED"


def get_verbose_devices() -> set[str]:
    """Devices whose terminal tabs the restart launcher opened.

    This is only a viewer selection. Every device writes a log file; the Devices page tails
    those files whether or not they were ticked.
    """
    raw = os.getenv("ALABOS_VERBOSE_DEVICES", "")
    return {device.strip() for device in raw.split(",") if device.strip()}


def default_verbose_log_dir() -> Path:
    """Where device logs go when the restart launcher did not pick a per-launch folder."""
    local_app_data = os.environ.get("LOCALAPPDATA")
    if local_app_data:
        return Path(local_app_data) / "alab_one" / "device_logs"
    return Path.home() / ".alab_one" / "device_logs"


def get_verbose_log_dir() -> Path:
    raw = os.getenv("ALABOS_VERBOSE_LOG_DIR", "").strip()
    if raw:
        return Path(raw)
    return default_verbose_log_dir()


def verbose_device_logging_enabled() -> bool:
    return True


def is_verbose_device(device_name: str) -> bool:
    """Whether the launcher opened a terminal tab for this device."""
    return device_name in get_verbose_devices()


def should_trace_device(device_name: str) -> bool:  # noqa: ARG001
    """Every device is traced so the Devices page has something to show."""
    return True


def should_trace_mobile_robot() -> bool:
    return True


def should_trace_robot_arm_mobile() -> bool:
    return True


def log_verbose_device(device_name: str, message: str, *args: object) -> None:
    log_dir = get_verbose_log_dir()
    log_dir.mkdir(parents=True, exist_ok=True)
    text = message % args if args else message
    timestamp = datetime.now().strftime("%H:%M:%S")
    line = f"[{timestamp}] {text}\n"
    log_path = log_dir / f"{device_name}.log"
    with log_path.open("a", encoding="utf-8") as handle:
        handle.write(line)


def emit_device_trace(device_name: str, message: str, *args: object) -> None:
    text = message % args if args else message
    log_verbose_device(device_name, "[device-rpc] " + text)


def prepare_verbose_log_files(device_names: list[str], log_dir: Path) -> None:
    log_dir.mkdir(parents=True, exist_ok=True)
    for device_name in device_names:
        log_path = log_dir / f"{device_name}.log"
        log_path.write_text("", encoding="utf-8")


#: How many trailing lines the dashboard asks for. The terminal tabs show the same window.
DEFAULT_VERBOSE_LOG_TAIL = 200
MAX_VERBOSE_LOG_TAIL = 1000
_TAIL_READ_CHUNK = 65536


def _safe_verbose_log_name(device_name: str) -> str:
    """Return the log filename stem, or raise if ``device_name`` could escape the log directory."""
    if not device_name or any(part in device_name for part in ("/", "\\", "..")):
        raise ValueError(f"Invalid device name: {device_name!r}")
    return device_name


def read_verbose_log_tail(
    device_name: str, max_lines: int = DEFAULT_VERBOSE_LOG_TAIL
) -> dict:
    """The same trailing lines the restart-launcher terminal tab is following.

    Returns a dict with ``available``, ``reason``, and ``lines``. ``reason`` is ``no_file``
    when this device has not written a line yet, and ``None`` when the file exists.
    """
    _safe_verbose_log_name(device_name)
    if max_lines < 1:
        max_lines = 1
    if max_lines > MAX_VERBOSE_LOG_TAIL:
        max_lines = MAX_VERBOSE_LOG_TAIL

    log_path = get_verbose_log_dir() / f"{device_name}.log"
    if not log_path.is_file():
        return {"available": False, "reason": "no_file", "lines": []}

    return {
        "available": True,
        "reason": None,
        "lines": _tail_text_lines(log_path, max_lines),
    }


def _tail_text_lines(path: Path, max_lines: int) -> list[str]:
    """Read the last ``max_lines`` of a file without loading the whole thing.

    A half-gigabyte launch log is what made this necessary: ``read()`` of the whole file is how
    we used to hang when we only needed the end.
    """
    size = path.stat().st_size
    if size == 0:
        return []
    to_read = min(size, _TAIL_READ_CHUNK)
    with path.open("rb") as handle:
        handle.seek(-to_read, os.SEEK_END)
        data = handle.read()
    text = data.decode("utf-8", errors="replace")
    lines = text.splitlines()
    # Seeking into the middle of a line leaves a truncated first entry; drop it.
    if size > to_read and lines:
        lines = lines[1:]
    return lines[-max_lines:]
