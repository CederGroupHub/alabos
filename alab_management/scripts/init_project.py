from pathlib import Path

from monty import shutil


def init_project():
    """
    Initialize a new project with default definitions (../_default)
    """
    default_project_folder = (Path(__file__).parent / ".." / "_default").absolute()
    working_dir = Path.cwd()
    if any(working_dir.iterdir()):
        raise FileExistsError("Expect an empty folder! But current folder is not empty")
    shutil.copy_r(default_project_folder.as_posix(), working_dir.as_posix())

    return True
