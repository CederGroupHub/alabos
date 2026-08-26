import logging
import os
from collections.abc import Mapping

from rich.console import Console
from rich.logging import RichHandler

DEVICE_RPC_LOGGER = "alab_management.device_manager"
MOBILE_ROBOT_ARM_LOGGER = "alab_control.mobile_robot_arm.mobile_robot_arm"
ROBOT_ARM_MOBILE_LOGGER = "alab_one.alabOS.devices.robot_arm_mobile"
DEVICE_RPC_HEARTBEAT_SECONDS = 30.0

NOISY_LOGGERS = (
    "pika",
    "paramiko",
    "urllib3",
    "pymongo",
    "gevent",
)

LAB_PACKAGES = (
    "alab_management",
    "alab_one",
    "alab_control",
)

_LOGGING_CONFIGURED = False


def set_up_rich_handler(logger: logging.Logger) -> RichHandler:
    """Set up a RichHandler for a logger."""
    rich_handler = RichHandler(
        rich_tracebacks=True,
        markup=True,
        show_path=False,
        show_level=False,
        console=Console(force_terminal=True),
    )
    rich_handler.setFormatter(logging.Formatter("%(message)s", datefmt="[%X]"))
    logger.addHandler(rich_handler)
    return rich_handler


def _get_logging_config() -> dict:
    try:
        from alab_management.config import AlabOSConfig

        logging_config = AlabOSConfig().get("logging", {})
        if isinstance(logging_config, Mapping):
            return dict(logging_config)
    except FileNotFoundError:
        pass
    return {}


def _logging_flag_from_env(env_var: str) -> bool | None:
    env_value = os.getenv(env_var, "").strip().lower()
    if env_value in {"1", "true", "yes", "on"}:
        return True
    if env_value in {"0", "false", "no", "off"}:
        return False
    return None


def _is_logging_debug_enabled(config_key: str, env_var: str) -> bool:
    env_result = _logging_flag_from_env(env_var)
    if env_result is not None:
        return env_result
    return bool(_get_logging_config().get(config_key, False))


def is_device_rpc_debug_enabled() -> bool:
    """Return True when verbose device RPC tracing should go to the terminal."""
    return _is_logging_debug_enabled("device_rpc_debug", "ALABOS_DEVICE_RPC_DEBUG")


def is_mobile_robot_debug_enabled() -> bool:
    """Return True when verbose Ability HTTP tracing should go to the terminal."""
    return _is_logging_debug_enabled("mobile_robot_debug", "ALABOS_MOBILE_ROBOT_DEBUG")


def is_robot_arm_mobile_debug_enabled() -> bool:
    """Return True when verbose RobotArmMobile orchestration tracing is enabled."""
    return _is_logging_debug_enabled(
        "robot_arm_mobile_debug",
        "ALABOS_ROBOT_ARM_MOBILE_DEBUG",
    )


def _setup_trace_logger(logger_name: str) -> None:
    trace_logger = logging.getLogger(logger_name)
    trace_logger.handlers.clear()
    trace_logger.setLevel(logging.INFO)
    trace_logger.propagate = False
    set_up_rich_handler(trace_logger)


def configure_logging(
    *,
    dramatiq_level: int = logging.WARNING,
    device_rpc_debug: bool | None = None,
    mobile_robot_debug: bool | None = None,
    robot_arm_mobile_debug: bool | None = None,
    announce: bool = True,
) -> None:
    """Configure logging for an AlabOS or ALab One process.

    Root and third-party libraries stay quiet at WARNING while lab package
    loggers share Rich console handlers at INFO.

    Verbose terminal tracing can be toggled in ``alabos_config.toml``:

    .. code-block:: toml

        [logging]
        device_rpc_debug = true
        mobile_robot_debug = true
        robot_arm_mobile_debug = true

    Environment overrides: ``ALABOS_DEVICE_RPC_DEBUG``,
    ``ALABOS_MOBILE_ROBOT_DEBUG``, ``ALABOS_ROBOT_ARM_MOBILE_DEBUG``.
    """
    global _LOGGING_CONFIGURED
    if _LOGGING_CONFIGURED:
        return

    root = logging.getLogger()
    root.handlers.clear()
    root.setLevel(logging.WARNING)

    for name in NOISY_LOGGERS:
        logging.getLogger(name).setLevel(logging.WARNING)
    logging.getLogger("dramatiq").setLevel(dramatiq_level)

    for package in LAB_PACKAGES:
        pkg_logger = logging.getLogger(package)
        pkg_logger.handlers.clear()
        pkg_logger.setLevel(logging.INFO)
        pkg_logger.propagate = False
        set_up_rich_handler(pkg_logger)

    for name, candidate in logging.root.manager.loggerDict.items():
        if not isinstance(name, str):
            continue
        if not any(name.startswith(f"{package}.") for package in LAB_PACKAGES):
            continue
        if not isinstance(candidate, logging.Logger):
            continue
        candidate.handlers = [
            handler
            for handler in candidate.handlers
            if not isinstance(handler, RichHandler)
        ]
        candidate.propagate = True

    if device_rpc_debug is None:
        device_rpc_debug = is_device_rpc_debug_enabled()
    if mobile_robot_debug is None:
        mobile_robot_debug = is_mobile_robot_debug_enabled()
    if robot_arm_mobile_debug is None:
        robot_arm_mobile_debug = is_robot_arm_mobile_debug_enabled()

    enabled_traces: list[str] = []
    if device_rpc_debug:
        _setup_trace_logger(DEVICE_RPC_LOGGER)
        enabled_traces.append("device RPC")
    if mobile_robot_debug:
        _setup_trace_logger(MOBILE_ROBOT_ARM_LOGGER)
        enabled_traces.append("mobile robot HTTP")
    if robot_arm_mobile_debug:
        _setup_trace_logger(ROBOT_ARM_MOBILE_LOGGER)
        enabled_traces.append("robot arm mobile")

    if announce and enabled_traces:
        logging.getLogger("alab_management").info(
            "Verbose tracing enabled (%s)", ", ".join(enabled_traces)
        )

    _LOGGING_CONFIGURED = True
