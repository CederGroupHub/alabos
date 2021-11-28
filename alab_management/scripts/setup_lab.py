"""
Generate device, sample position, task definitions from user defined files (task & device)
and write them to MongoDB, which will make it easier to query
"""


def setup_lab():
    """
    Cleanup the db and then import all the definitions and set up the db
    """
    from ..utils.module_ops import load_definition
    from ..device_view import get_all_devices, DeviceView
    from ..sample_view import SampleView

    load_definition()
    devices = get_all_devices().values()
    DeviceView().add_devices_to_db()
    SampleView().add_sample_positions_to_db(
        [sample_pos for device in devices for sample_pos in device.sample_positions])

    return True
