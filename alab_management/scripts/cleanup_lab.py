"""
To remove all the device, sample position definition from database
"""

from ..device_view import DeviceView
from ..sample_view import SampleView


def cleanup_lab():
    """
    Drop device, sample_position collection from MongoDB
    """
    DeviceView().clean_up_device_collection()
    SampleView().clean_up_sample_position_collection()
