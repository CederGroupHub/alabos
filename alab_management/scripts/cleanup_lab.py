"""
To remove all the device, sample position definition from database.

If ``-a`` is true, the whole database (including the data recorded) shall
be deleted.
"""


def cleanup_lab(all_collections: bool = False, _force_i_know_its_dangerous: bool = False):
    """Drop device, sample_position collection from MongoDB."""
    from alab_management.config import AlabConfig  # type: ignore
    from alab_management.device_view.device_view import DeviceView
    from alab_management.sample_view.sample_view import SampleView
    from alab_management.utils.data_objects import _GetMongoCollection
    import pymongo


    _GetMongoCollection.init()
    config = AlabConfig()
    task_count_new = _GetMongoCollection.client.get_database(config['general']['name']).get_collection("tasks").count_documents({})
    if all_collections:
        if not _force_i_know_its_dangerous:
            y = input(
                f"Are you sure you want to remove the whole database? "
                f"It will purge all of your data [{task_count_new} entries] in {config['mongodb']['host']}, "
                f"which cannot be recovered. [y/n]: "
            )
            if y != "y":
                return False
        z = input(f"Write the name of the database that you want to remove. If you want to remove the simulation database then type in {config['general']['name']}: ")
        if z == config["general"]["name"] and z != "Alab":
            _GetMongoCollection.client.drop_database(config["general"]["name"])  # type: ignore
        else:
            print("Wrong name of database. Hence, not removed.")
            return False
    DeviceView()._clean_up_device_collection()
    SampleView().clean_up_sample_position_collection()
    _GetMongoCollection.get_collection("_lock").drop()
    _GetMongoCollection.get_collection("requests").drop()
    return True
