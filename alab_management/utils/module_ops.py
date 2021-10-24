import importlib
import sys
from pathlib import Path

from .typing_ops import is_typing


def import_module_from_path(path):
    path = Path(path)
    sys.path.insert(0, path.parent.as_posix())
    try:
        module = importlib.import_module(path.name)
    except AttributeError as e:
        e.args = (e.args[0] + " Maybe there is some bugs in your definition, please check that.")
        raise
    return module


def get_full_cls_name(cls):
    module = cls.__module__
    if module == 'builtins':
        return cls.__qualname__  # avoid outputs like 'builtins.str'
    elif is_typing(cls):  # typing class
        return cls.__repr__()
    return module + '.' + cls.__qualname__
