"""This file contains the functions to load python modules from a path."""

import importlib
import importlib.util
import os.path
import sys
from copy import copy
from pathlib import Path
from types import ModuleType


def import_module_from_path(path: str | Path) -> ModuleType:
    """Import a module by its path. If it is a subpackage, keep going back and import the parent package."""
    path = Path(path).resolve()
    dir_path = path.parent if path.is_file() else path

    # Go up to the topmost package
    while (dir_path.parent / "__init__.py").exists():
        dir_path = dir_path.parent

    # Add the top-level package path to sys.path
    if str(dir_path.parent) not in sys.path:
        sys.path.insert(0, str(dir_path.parent))

    # Determine module name by relative path from top-level package
    rel_path = path.relative_to(dir_path.parent)
    module_name = ".".join(rel_path.with_suffix("").parts)
    # Import the module
    return importlib.import_module(module_name, module_name)


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
