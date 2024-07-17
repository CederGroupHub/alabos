import os
from pathlib import Path

from alab_management import add_device, add_standalone_sample_position, add_task

# set the config path to the default config file
os.putenv("ALABOS_CONFIG_PATH", Path(__file__).parent.absolute() / "config.toml")
