"""
Generate device, sample position, task definitions from user defined files (task & device)
and write them to MongoDB, which will make it easier to query
"""

from ..device_view import get_all_devices, DeviceView
from ..sample_view import SampleView
from ..utils.module_ops import load_definition


def setup_from_device_def():
    """
    Set up sample positions, devices from user's device definition, whose path is
    specified by ``config["devices"]["device_dir"]``
    """
    devices = get_all_devices().values()
    DeviceView().add_devices_to_db()
    SampleView().add_sample_positions_to_db([sample_pos
                                             for device in devices
                                             for sample_pos in device.sample_positions])


def setup_lab():
    """
    Cleanup the db and then import all the definitions and set up the db
    """
    load_definition()
    setup_from_device_def()
