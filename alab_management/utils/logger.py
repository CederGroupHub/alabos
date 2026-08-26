import logging

from rich.console import Console
from rich.logging import RichHandler

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


def configure_logging(*, dramatiq_level: int = logging.WARNING) -> None:
    """Configure logging for an AlabOS or ALab One process.

    Root and third-party libraries stay quiet at WARNING while lab package
    loggers share Rich console handlers at INFO.
    """
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
