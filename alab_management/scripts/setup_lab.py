"""
Generate device, sample position, task definitions from user defined files (task & device)
and write them to MongoDB, which will make it easier to query
"""


from alab_management.sample_view.sample import SamplePosition


def setup_lab():
    """
    Cleanup the db and then import all the definitions and set up the db
    """
    from ..utils.module_ops import load_definition
    from ..device_view import get_all_devices, DeviceView
    from ..sample_view import SampleView
    from ..sample_view.sample import get_all_standalone_sample_positions

    load_definition()
    devices = get_all_devices().values()
    DeviceView().add_devices_to_db()
    sample_positions = list(
        get_all_standalone_sample_positions().values()
    )  # start with all standalone sample positions
    for device in devices:  # prepend device name to device sample positions
        for pos in device.sample_positions:
            sample_positions.append(
                SamplePosition(
                    name=f"{device.name}{pos.SEPARATOR}{pos.name}",
                    description=pos.description,
                    number=pos.number,
                )
            )
    SampleView().add_sample_positions_to_db(sample_positions)

    return True
