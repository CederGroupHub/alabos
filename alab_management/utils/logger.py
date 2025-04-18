import logging

from rich.console import Console
from rich.logging import RichHandler


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
