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

    Returns
    -------
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
    """Metaclass for classes that need to ensure that the import lock is acquired."""

    def __new__(mcs, name, bases, attrs):
        """Using locks to ensure that the import of the config folder does not happen while the class is being created."""
        # We need to avoid importing the config folder during creation of the class.
        with import_lock:
            new_class = super().__new__(mcs, name, bases, attrs)
        return new_class


def deep_reload(module):
    """Recursively reloads a module and all its submodules."""
    if not isinstance(module, ModuleType):
        raise TypeError("Expected a module object")
    importlib.reload(module)

    already_reloaded = set()
    # Reload all submodules
    for attribute_name in dir(module):
        attribute = getattr(module, attribute_name)
        if (
            isinstance(attribute, ModuleType)
            and attribute.__name__.startswith(module.__name__)
            and attribute.__name__ not in already_reloaded
        ):
            deep_reload(attribute)
            already_reloaded.add(attribute.__name__)

    module = importlib.reload(module)
    return module


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
            print("Reloading module:", module_name)
            # Set an environment variable to indicate reloading, used in add_device, add_task, add_sample_position
            os.environ["ALABOS_RELOAD"] = "1"
            try:
                # First, scan for new modules that might not be imported yet
                if reload:
                    _scan_and_import_new_modules(path)
                return deep_reload(sys.modules[module_name])
            finally:
                os.environ.pop("ALABOS_RELOAD", None)
        return importlib.import_module(module_name, module_name)


def _scan_and_import_new_modules(root_path: Path) -> None:
    """
    Scan for new Python modules in the given path and import them.
    This ensures that new packages/definitions are discovered during reload.
    """
    if not root_path.is_dir():
        return

    # Use the same logic as import_module_from_path to find the top-level package
    dir_path = root_path
    while (dir_path.parent / "__init__.py").exists():
        dir_path = dir_path.parent

    # Collect all Python files and sort them by depth (submodules first)
    python_files = []
    for py_file in root_path.rglob("*.py"):
        if py_file.name == "__init__.py":
            continue
        # Calculate depth (number of parts in relative path)
        rel_path = py_file.relative_to(root_path)
        depth = len(rel_path.parts)
        python_files.append((depth, py_file))

    # Sort by depth (deepest first) to ensure submodules are imported before parent modules
    python_files.sort(key=lambda x: x[0], reverse=True)

    reloaded_packages = set()
    root_path = root_path.resolve()

    for _depth, py_file in python_files:
        try:
            rel_path = py_file.relative_to(dir_path.parent)
            module_name = ".".join(rel_path.with_suffix("").parts)

            # If this module is not already imported, import it
            if module_name not in sys.modules:
                print(f"Importing new module: {module_name}")
                importlib.import_module(module_name)

                # After importing, reload each parent package up to the working directory
                parent = py_file.parent
                while True:
                    # Stop if we've reached above the working directory
                    if parent.resolve() < root_path:
                        break
                    # Only reload if __init__.py exists
                    init_file = parent / "__init__.py"
                    if not init_file.exists():
                        parent = parent.parent
                        continue
                    # Calculate the package name
                    try:
                        rel_parent = parent.relative_to(dir_path.parent)
                        package_name = ".".join(rel_parent.parts)
                        if (
                            package_name
                            and package_name not in reloaded_packages
                            and package_name in sys.modules
                        ):
                            print(f"Reloading parent package: {package_name}")
                            try:
                                deep_reload(sys.modules[package_name])
                                reloaded_packages.add(package_name)
                            except Exception as e:
                                print(
                                    f"Failed to reload parent package {package_name}: {e}"
                                )
                    except ValueError:
                        # parent is not under dir_path.parent
                        break
                    if parent.resolve() == root_path:
                        break
                    parent = parent.parent
        except (ValueError, ImportError) as e:
            print(f"Skipping import of {py_file}: {e}")
            continue


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
