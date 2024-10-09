import os
from pathlib import Path

# keep this line at the top of the file
os.putenv("ALABOS_CONFIG_PATH", Path(__file__).parent.absolute() / "config.toml")

from alab_management import add_device, add_task

from .devices.claude import ClaudeLight
from .tasks.claude import MeasureRGB

# set the config path to the default config file


add_device(ClaudeLight(name="rgb"))
add_task(MeasureRGB)

