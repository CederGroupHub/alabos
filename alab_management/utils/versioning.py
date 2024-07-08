"""This file contains the functions to get the current version of the alabos either by commit hash or arbitrary versioning."""

import os
import subprocess
from copy import copy
from pathlib import Path


def get_version():
    """Get the current version of the alabos either by git commit_hash system or manual."""
    from alab_management.config import AlabOSConfig

    config = AlabOSConfig()
    versioning_style = config["versioning"]["versioning_style"]
    working_dir = config["general"]["working_dir"]

    dir_to_import_from = copy(working_dir)
    dir_to_import_from = (
        Path(dir_to_import_from)
        if os.path.isabs(dir_to_import_from)
        else config.path.parent / dir_to_import_from
    )
    # get current directory
    current_dir = Path(os.getcwd())
    if versioning_style == "manual":
        return config["versioning"]["version"]
    elif versioning_style == "git":
        # change to the directory to import from and get the commit hash
        os.chdir(dir_to_import_from)
        commit_hash = (
            subprocess.check_output(["git", "rev-parse", "HEAD"]).decode().strip()
        )
        # change back to the previous directory where the script was run
        os.chdir(current_dir)
        return commit_hash
