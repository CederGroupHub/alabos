import importlib
import sys
from pathlib import Path


def import_module_from_path(path):
    path = Path(path)
    sys.path.insert(0, path.parent.as_posix())
    return importlib.import_module(path.name)
