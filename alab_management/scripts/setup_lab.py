"""
Generate device, sample position, task definitions from user defined files (task & device)
and write them to MongoDB, which will make it easier to query.
"""


def setup_lab():
    """Cleanup the db and then import all the definitions and set up the db."""
    from alab_management.device_view import DeviceView, get_all_devices
    from alab_management.sample_view import SampleView
    from alab_management.sample_view.sample import get_all_standalone_sample_positions
    from alab_management.utils.module_ops import load_definition

    load_definition()
    devices = get_all_devices().values()
    DeviceView().add_devices_to_db()
    for device_instance in devices:
        device_instance._apply_default_db_values()
        # trigger database updates for Device values stored within db. These are not executed upon instantiation because the device documents were not yet created within the Device collection.

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
