"""Per-device verbose logging to files for the restart launcher."""

from __future__ import annotations

import os
from datetime import datetime
from pathlib import Path

MOBILE_ROBOT_DEVICE_NAME = "MOBILE_arm_ALFRED"


def get_verbose_devices() -> set[str]:
    raw = os.getenv("ALABOS_VERBOSE_DEVICES", "")
    return {device.strip() for device in raw.split(",") if device.strip()}


def get_verbose_log_dir() -> Path | None:
    raw = os.getenv("ALABOS_VERBOSE_LOG_DIR", "").strip()
    if not raw:
        return None
    return Path(raw)


def verbose_device_logging_enabled() -> bool:
    return bool(get_verbose_devices() and get_verbose_log_dir())


def is_verbose_device(device_name: str) -> bool:
    return device_name in get_verbose_devices()


def should_trace_device(device_name: str) -> bool:
    verbose_devices = get_verbose_devices()
    if verbose_devices:
        return device_name in verbose_devices
    from alab_management.utils.logger import is_device_rpc_debug_enabled

    return is_device_rpc_debug_enabled()


def should_trace_mobile_robot() -> bool:
    if is_verbose_device(MOBILE_ROBOT_DEVICE_NAME):
        return True
    try:
        from alab_management.utils.logger import is_mobile_robot_debug_enabled

        return is_mobile_robot_debug_enabled()
    except ImportError:
        return False


def should_trace_robot_arm_mobile() -> bool:
    if is_verbose_device(MOBILE_ROBOT_DEVICE_NAME):
        return True
    try:
        from alab_management.utils.logger import is_robot_arm_mobile_debug_enabled

        return is_robot_arm_mobile_debug_enabled()
    except ImportError:
        return False


def log_verbose_device(device_name: str, message: str, *args: object) -> None:
    if not is_verbose_device(device_name):
        return
    log_dir = get_verbose_log_dir()
    if log_dir is None:
        return
    log_dir.mkdir(parents=True, exist_ok=True)
    text = message % args if args else message
    timestamp = datetime.now().strftime("%H:%M:%S")
    line = f"[{timestamp}] {text}\n"
    log_path = log_dir / f"{device_name}.log"
    with log_path.open("a", encoding="utf-8") as handle:
        handle.write(line)


def emit_device_trace(device_name: str, message: str, *args: object) -> None:
    text = message % args if args else message
    if is_verbose_device(device_name):
        log_verbose_device(device_name, "[device-rpc] " + text)
        return
    from alab_management.utils.logger import is_device_rpc_debug_enabled

    if is_device_rpc_debug_enabled():
        import logging

        logging.getLogger("alab_management.device_manager").info(
            "[device-rpc] " + text
        )


def prepare_verbose_log_files(device_names: list[str], log_dir: Path) -> None:
    log_dir.mkdir(parents=True, exist_ok=True)
    for device_name in device_names:
        log_path = log_dir / f"{device_name}.log"
        log_path.write_text("", encoding="utf-8")
