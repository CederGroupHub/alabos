import importlib
import os.path
import re
import sys
from pathlib import Path
from typing import Union


def import_module_from_path(path: Union[str, Path]):
    """
    Import a module by its path
    """
    if not isinstance(path, Path):
        path = Path(path)
    sys.path.insert(0, path.parent.as_posix())
    try:
        module = importlib.import_module(path.name)
    except AttributeError as exception:
        exception.args = (exception.args[0] + " Maybe there is some bugs in your definition, please check that.")
        raise
    sys.path.pop(0)
    return module


def load_definition():
    """
    Load device and task definitions from file (specified in config file)
    """
    from ..config import AlabConfig

    config = AlabConfig()

    import_module_from_path(config.path.parent / config["general"]["working_dir"]
                            if not os.path.isabs(config["general"]["working_dir"])
                            else Path(config["general"]["definition_dir"]))


def import_device_definitions(file_folder: str, module_name: str):
    """
    Import device definition from files, which should be a instance of ``BaseDevice``, and we will
    call ``add_device`` to register them automatically

    Args:
        file_folder: the folder that contains the device instances
        module_name: the name of module
    """
    from ..device_view.device import BaseDevice, add_device, get_all_devices

    file_folder_path = Path(file_folder).parent

    for path in file_folder_path.iterdir():
        file_name = path.relative_to(file_folder_path)
        if re.match(r'^[a-zA-Z][a-zA-Z0-9_]*(\.py)?$', file_name.name) is None:
            continue
        device_module = importlib.import_module("." + re.sub(r'(\.py)$', '', path.name), package=module_name)

        for v in device_module.__dict__.values():
            if (isinstance(v, BaseDevice)
                    and v not in get_all_devices().values()):
                add_device(v)


def import_task_definitions(file_folder: str, module_name: str):
    """
    Import task definitions from files, which should be a subclass of ``BaseTask``, and we will
    call ``add_task`` to register them automatically

    Args:
        file_folder: the folder that contains the device instances
        module_name: the name of module
    """
    from ..task_view.task import BaseTask, add_task, get_all_tasks

    file_folder_path = Path(file_folder).parent

    for path in file_folder_path.iterdir():
        file_name = path.relative_to(file_folder_path)
        if re.match(r'^[a-zA-Z][a-zA-Z0-9_.]*(\.py)?$', file_name.name) is None:
            continue
        task_module = importlib.import_module("." + re.sub(r'(\.py)$', '', path.name), package=module_name)

        for v in task_module.__dict__.values():
            if (isinstance(v, type)
                    and v is not BaseTask
                    and issubclass(v, BaseTask)
                    and v not in get_all_tasks().values()):
                add_task(v)
