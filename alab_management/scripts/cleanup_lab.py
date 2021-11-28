"""
To remove all the device, sample position definition from database

If ``-a`` is true, the whole database (including the data recorded) shall
be deleted.
"""


def cleanup_lab(all_collections: bool = False):
    """
    Drop device, sample_position collection from MongoDB
    """
    from ..config import AlabConfig
    from ..db import _GetCollection
    from ..device_view.device_view import DeviceView
    from ..sample_view.sample_view import SampleView

    config = AlabConfig()
    if all_collections:
        y = input(f"Are you sure you want to remove the whole database? "
                  f"It will purge all of your data in {config['db']['name']}, "
                  f"which cannot be recovered. [yN]: ")
        if y != "y":
            return False
        _GetCollection.init()
        _GetCollection.client.drop_database(config['db']['name'])  # type: ignore
    DeviceView().clean_up_device_collection()
    SampleView().clean_up_sample_position_collection()
    return True
