"""This file contains the functions to load python modules from a path."""

import hashlib
import importlib
import importlib.util
import os
import os.path
import sys
import threading
from abc import ABCMeta
from copy import copy
from pathlib import Path
from types import ModuleType

import_lock = threading.RLock()


def hash_python_files_in_folder(folder_path: str | Path, file_exts=(".py",)):
    """
    Recursively calculate SHA256 hash of all .py files in a folder.

    Args:
        folder_path: root directory path as string
        file_exts: tuple of file extensions to include (default: .py only)

    Returns:
        SHA256 hash as hex digest
    """
    folder = Path(folder_path)

    if not folder.is_dir():
        raise ValueError(f"{folder_path} is not a valid directory")

    # Collect all matching files
    source_files = [
        path
        for path in folder.rglob("*")
        if path.is_file() and path.suffix in file_exts
    ]

    # Sort for consistent ordering
    source_files.sort()

    hash_obj = hashlib.sha256()

    for filepath in source_files:
        with open(filepath, "rb") as f:
            content = f.read()
            hash_obj.update(
                str(filepath.relative_to(folder)).encode("utf-8")
            )  # relative path
            hash_obj.update(content)

    return hash_obj.hexdigest()


class MetaClassWithImportLock(ABCMeta):
    """
    Metaclass for classes that need to ensure that the import lock is acquired
    """

    def __new__(mcs, name, bases, attrs):
        # We need to avoid importing the config folder during creation of the class.
        with import_lock:
            new_class = super().__new__(mcs, name, bases, attrs)
        return new_class


def import_module_from_path(path: str | Path, reload: bool = False) -> ModuleType:
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
    with import_lock:
        if module_name in sys.modules and reload:
            # Set an environment variable to indicate reloading, used in add_device, add_task, add_sample_position
            os.environ["ALABOS_RELOAD"] = "1"
            try:
                return importlib.reload(sys.modules[module_name])
            finally:
                os.environ.pop("ALABOS_RELOAD", None)
        return importlib.import_module(module_name, module_name)


def load_definition(reload: bool = False) -> None:
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

    import_module_from_path(dir_to_import_from, reload=reload)


def calculate_package_hash():
    """Calculate the hash of all python files in the working directory."""
    from alab_management.config import AlabOSConfig

    config = AlabOSConfig()
    working_dir = config["general"]["working_dir"]

    dir_to_import_from = copy(working_dir)
    dir_to_import_from = (
        Path(dir_to_import_from)
        if os.path.isabs(dir_to_import_from)
        else config.path.parent / dir_to_import_from
    )

    return hash_python_files_in_folder(dir_to_import_from, file_exts=(".py", ".pyc"))
