import subprocess
import tempfile
from pathlib import Path


def test_init_command():
    # Run the command
    with tempfile.TemporaryDirectory() as tmpdirname_:
        tmpdirname = Path(tmpdirname_)
        subprocess.run(
            ["alabos", "init"], stdout=subprocess.PIPE, check=True, cwd=tmpdirname
        )

        # Check that the files were created
        assert (tmpdirname / "pyproject.toml").exists()
        assert (tmpdirname / "alabos_project" / "config.toml").exists()
        assert (
            tmpdirname / "alabos_project" / "devices" / "default_device.py"
        ).exists()
        assert (tmpdirname / "alabos_project" / "tasks" / "default_task.py").exists()
