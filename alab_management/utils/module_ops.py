"""This file contains the functions to load python modules from a path."""

import importlib
import os.path
import sys
from copy import copy
from pathlib import Path

__imported_modules__ = {}


def import_module_from_path(path: str | Path, parent_package: str | None = None):
    """Import a module by its path."""
    if path in __imported_modules__:  # Avoid importing the same module twice
        return __imported_modules__[path]
    if not isinstance(path, Path):
        path = Path(path)
    sys.path.insert(0, path.parent.as_posix())
    try:
        module = importlib.import_module(path.name, parent_package)
    except AttributeError as exception:
        exception.args = (
            exception.args[0]
            + " Maybe there is some bugs in your definition, please check that."
        )
        raise
    sys.path.pop(0)
    __imported_modules__[path] = module
    return module


def load_definition():
    """Load device and task definitions from file (specified in config file)."""
    from alab_management.config import AlabOSConfig

    config = AlabOSConfig()
    working_dir = config["general"]["working_dir"]

    dir_to_import_from = copy(working_dir)
    dir_to_import_from = (
        Path(dir_to_import_from)
        if os.path.isabs(dir_to_import_from)
        else config.path.parent / dir_to_import_from
    )

    import_module_from_path(dir_to_import_from)
