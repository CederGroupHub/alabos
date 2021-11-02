"""
To remove all the device, sample position definition from database
"""

from ..config import config
from ..db import get_collection


def cleanup_lab():
    """
    Drop device, sample_position collection from MongoDB
    """
    device_collection = get_collection(config["devices"]["device_db"])
    sample_position_collection = get_collection(config["sample_positions"]["sample_db"] + "_position")

    device_collection.drop()
    sample_position_collection.drop()
