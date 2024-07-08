"""
Generate device, sample position, task definitions from user defined files (task & device)
and write them to MongoDB, which will make it easier to query.
"""

import os
import shutil
from copy import copy
from pathlib import Path


def setup_lab():
    """Cleanup the db and then import all the definitions and set up the db."""
    # create a new folder in the version control folder inside working directory if it does not exist
    from alab_management.config import AlabOSConfig
    from alab_management.device_view import DeviceView, get_all_devices
    from alab_management.sample_view import SampleView
    from alab_management.sample_view.sample import get_all_standalone_sample_positions
    from alab_management.utils.module_ops import load_definition
    from alab_management.utils.versioning import get_version

    config = AlabOSConfig()
    working_dir = config["general"]["working_dir"]

    dir_to_import_from = copy(working_dir)
    dir_to_import_from = (
        Path(dir_to_import_from)
        if os.path.isabs(dir_to_import_from)
        else config.path.parent / dir_to_import_from
    )
    versions_dir = os.listdir(dir_to_import_from / "versions")
    current_version = get_version()
    if current_version not in versions_dir:
        os.mkdir(dir_to_import_from / "versions" / current_version)
        # copy all the folders and files other than versions folder to the new folder using shutil
        folders = [
            entry
            for entry in os.listdir(dir_to_import_from)
            if os.path.isdir(os.path.join(dir_to_import_from, entry))
        ]
        files = [
            entry
            for entry in os.listdir(dir_to_import_from)
            if os.path.isfile(os.path.join(dir_to_import_from, entry))
        ]
        for folder in folders:
            if folder != "versions":
                # copy the folder to the new folder
                shutil.copytree(
                    dir_to_import_from / folder,
                    dir_to_import_from / "versions" / current_version / folder,
                )
        for file in files:
            shutil.copy(
                dir_to_import_from / file,
                dir_to_import_from / "versions" / current_version / file,
            )

    load_definition(current_version)
    devices = get_all_devices().values()
    DeviceView().add_devices_to_db()
    for device_instance in devices:
        device_instance._apply_default_db_values()
        # trigger database updates for Device values stored within db. These are not executed upon instantiation
        # because the device documents were not yet created within the Device collection.

    sample_view = SampleView()

    # start with all standalone sample positions
    sample_positions = list(get_all_standalone_sample_positions().values())
    sample_view.add_sample_positions_to_db(
        sample_positions=sample_positions, parent_device_name=None
    )
    # next add positions within devices
    for device in devices:  # prepend device name to device sample positions
        sample_view.add_sample_positions_to_db(
            sample_positions=device.sample_positions, parent_device_name=device.name
        )

    return True
