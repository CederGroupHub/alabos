"""
To remove all the device, sample position definition from database.

If ``-a`` is true, the whole database (including the data recorded) shall
be deleted.
"""
from labgraph.views.base import NotFoundInDatabaseError


def cleanup_lab(
    all_collections: bool = False, _force_i_know_its_dangerous: bool = False
):
    """Drop device, sample_position collection from MongoDB."""
    from alab_management.config import AlabConfig
    from alab_management.device_view.device_view import DeviceView
    from alab_management.sample_view.sample_view import SampleView
    from alab_management.utils.data_objects import _GetMongoCollection

    config = AlabConfig()
    if all_collections:
        if not _force_i_know_its_dangerous:
            y = input(
                f"Are you sure you want to remove the whole database? "
                f"It will purge all of your data in {config['mongodb']['host']}, "
                f"which cannot be recovered. [yN]: "
            )
            if y != "y":
                return False
        _GetMongoCollection.init()
        for alabos_collection in ["abortable", "experiments", "tasks"]:
            _GetMongoCollection.get_collection(alabos_collection).drop()
    try:
        DeviceView()._clean_up_device_collection()
    except NotFoundInDatabaseError:
        pass
    try:
        SampleView().clean_up_sample_position_collection()
    except NotFoundInDatabaseError:
        pass
    _GetMongoCollection.get_collection("_lock").drop()
    _GetMongoCollection.get_collection("requests").drop()
    return True
