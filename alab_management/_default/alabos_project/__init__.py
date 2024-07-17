import os
from pathlib import Path

# set the config path to the default config file
# keep this line at the top of the file
os.putenv("ALABOS_CONFIG_PATH", Path(__file__).parent.absolute() / "config.toml")

# import/add devices and task from here

from alab_management import add_device, add_standalone_sample_position, add_task
