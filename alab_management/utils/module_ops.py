import importlib
import os.path
import sys
from pathlib import Path
from typing import Union, Type

from .typing_ops import is_typing
from ..config import config


def import_module_from_path(path: Union[str, Path]):
    """
    Import a module by its path
    """
    if not isinstance(path, Path):
        path = Path(path)
    sys.path.insert(0, path.parent.as_posix())
    try:
        module = importlib.import_module(path.name)
    except AttributeError as e:
        e.args = (e.args[0] + " Maybe there is some bugs in your definition, please check that.")
        raise
    sys.path.pop(0)
    return module


def load_definition():
    """
    Load device and task definitions from file (specified in config file)
    """
    import_module_from_path(config.path.parent / config["general"]["definition_dir"]
                            if not os.path.isabs(config["general"]["definition_dir"])
                            else Path(config["general"]["definition_dir"]))


def get_full_cls_name(cls: Type) -> str:
    """
    Get the cls's name as well as the path, e.g. ``a.b.C`` for class ``C``

    Returns:
        the name of cls
    """
    module = cls.__module__
    if module == 'builtins':
        return cls.__qualname__  # avoid outputs like 'builtins.str'
    elif is_typing(cls):  # typing class
        return cls.__repr__()
    return module + '.' + cls.__qualname__
