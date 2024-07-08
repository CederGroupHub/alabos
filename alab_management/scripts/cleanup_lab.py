"""
To remove all the device, sample position definition from database.

If ``-a`` is true, the whole database (including the data recorded) shall
be deleted.
"""

import os
import shutil
from copy import copy
from pathlib import Path


def cleanup_lab(
    all_collections: bool = False,
    _force_i_know_its_dangerous: bool = False,
    user_confirmation: str = None,
    sim_mode: bool = True,
    database_name: str = None,
    remove_versions: bool = True,
):
    """
    Drop device, sample_position collection from MongoDB.
    Can also drop the whole database if 'all_collections' is true.
    Can also remove the versions folder if 'remove_versions' is true.
    """
    from alab_management.config import AlabOSConfig  # type: ignore
    from alab_management.device_view.device_view import DeviceView
    from alab_management.sample_view.sample_view import SampleView
    from alab_management.utils.data_objects import _GetMongoCollection

    config = AlabOSConfig()
    if remove_versions:
        print("Removing versions folder")
        working_dir = config["general"]["working_dir"]
        dir_to_import_from = copy(working_dir)
        dir_to_import_from = (
            Path(dir_to_import_from)
            if os.path.isabs(dir_to_import_from)
            else config.path.parent / dir_to_import_from
        )
        versions_folders = [
            entry
            for entry in os.listdir(dir_to_import_from / "versions")
            if os.path.isdir(os.path.join(dir_to_import_from / "versions", entry))
        ]
        for version_folder in versions_folders:
            shutil.rmtree(dir_to_import_from / "versions" / version_folder)

    _GetMongoCollection.init()
    task_count_new = (
        _GetMongoCollection.client.get_database(config["general"]["name"])
        .get_collection("tasks")
        .count_documents({})
    )
    if all_collections:
        if not _force_i_know_its_dangerous:
            if user_confirmation is None:
                user_confirmation = input(
                    f"Are you sure you want to remove the whole database? "
                    f"It will purge all of your data [{task_count_new} entries] in {config['mongodb']['host']}, "
                    f"which cannot be recovered. [y/n]: "
                )
            if user_confirmation != "y":
                return False
        if database_name is None:
            database_name = input(
                f"Write the name of the database that you want to remove. "
                f"If you want to remove the simulation database then type in "
                f"{config['general']['name']}_sim:  "
            )
            print(f"Removing database {database_name}")
            _GetMongoCollection.init()
            _GetMongoCollection.client.drop_database(database_name)  # type: ignore
        else:
            print(f"Removing database {database_name}")
            _GetMongoCollection.init()
            _GetMongoCollection.client.drop_database(database_name)

        # if sim_mode != AlabOSConfig().is_sim_mode() or database_name == "Alab":
        #     print("Wrong name of database. Hence, not removed.")
        #     return False
        # elif sim_mode == AlabOSConfig().is_sim_mode() and database_name != "Alab":
        #     print(f"Removing database {database_name}")
        #     _GetMongoCollection.init()
        #     _GetMongoCollection.client.drop_database(database_name)  # type: ignore
        # else:
        #     print("Wrong name of database. Hence, not removed.")
        #     return False

    DeviceView()._clean_up_device_collection()
    SampleView().clean_up_sample_position_collection()
    _GetMongoCollection.get_collection("_lock").drop()
    _GetMongoCollection.get_collection("requests").drop()
    return True
