"""
To remove all the device, sample position definition from database

If ``-a`` is true, the whole database (including the data recorded) shall
be deleted.
"""

import click

from ..config import config
from ..db import _client
from ..device_view.device_view import DeviceView
from ..sample_view.sample_view import SampleView


def _cleanup_lab(all_collections: bool = False):
    """
    Drop device, sample_position collection from MongoDB
    """
    if all_collections:
        y = input(f"Are you sure you want to remove the whole database? "
                  f"It will purge all of your data in {config['db']['name']}, "
                  f"which cannot be recovered. [y/N]: ")
        if y.lower() != "y":
            return
        _client.drop_database(config['db']['name'])
    DeviceView().clean_up_device_collection()
    SampleView().clean_up_sample_position_collection()


@click.command()
@click.option("-a", "--all-collections", is_flag=True, default=False)
def cleanup_lab(all_collections: bool):
    _cleanup_lab(all_collections)
    print("Done")
