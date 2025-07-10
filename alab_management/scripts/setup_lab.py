"""
Generate device, sample position, task definitions from user defined files (task & device)
and write them to MongoDB, which will make it easier to query.
"""

from alab_management.alarm import Alarm
from alab_management.config import AlabOSConfig
from alab_management.device_view.device import get_current_devices
from alab_management.sample_view.sample import get_current_standalone_sample_positions


def setup_lab(
    reload: bool = False,
    return_removed_devices_and_sample_positions_names: bool = False,
):
    """Cleanup the db and then import all the definitions and set up the db."""
    from alab_management.device_view import (
        DeviceView,
        get_all_devices,
        reset_current_device_registry,
    )
    from alab_management.sample_view import (
        SampleView,
        reset_current_standalone_sample_position_registry,
    )
    from alab_management.sample_view.sample import get_all_standalone_sample_positions
    from alab_management.utils.module_ops import load_definition

    if reload:
        reset_current_device_registry()
        reset_current_standalone_sample_position_registry()
    load_definition(reload=reload)
    devices = (
        get_all_devices().values()
    )  # all device from the __init__.py and the ones that are currently connected
    current_devices = (
        get_current_devices()
    )  # all device from the __init__.py during this setup (only equals to devices if not reload)
    device_dict = (
        get_all_devices()
    )  # all device from the __init__.py and the ones that are currently connected
    all_available_devices = DeviceView().get_all()  # all device from the db
    available_devices_names = [
        device["name"] for device in all_available_devices
    ]  # all device names from the db
    filtered_devices = {}  # all device from the __init__.py that are not in the db
    for device_name in device_dict:
        if device_name not in available_devices_names:
            filtered_devices[device_name] = device_dict[
                device_name
            ]  # all device from the __init__.py that are not in the db
    print(f"current_devices_names: {list(current_devices.keys())}")
    print(f"available_devices_names: {available_devices_names}")
    removed_devices_names = (
        []
    )  # all device names from the db that are not in the __init__.py
    for device_name in available_devices_names:
        if device_name not in list(current_devices.keys()):
            removed_devices_names.append(device_name)
    print(f"Devices to be removed from the db and registry: {removed_devices_names}")
    DeviceView().add_devices_to_db(filtered_devices)
    for device_instance in devices:
        device_instance._apply_default_db_values()
        # trigger database updates for Device values stored within db. These are not executed upon instantiation
        # because the device documents were not yet created within the Device collection.

    sample_view = SampleView()

    # start with all standalone sample positions
    sample_positions = list(
        get_all_standalone_sample_positions().values()
    )  # all sample positions from the __init__.py and the ones that are currently in the lab
    sample_positions_names = list(
        get_all_standalone_sample_positions().keys()
    )  # all sample positions names from the __init__.py and the ones that are currently in the lab
    current_sample_positions_names = list(
        get_current_standalone_sample_positions().keys()
    )  # all sample positions from the __init__.py during this setup (only equals to sample_positions if not reload)

    # remove sample positions that are not in the lab anymore
    removed_sample_positions_names = []
    for sample_position_name in sample_positions_names:
        if sample_position_name not in current_sample_positions_names:
            removed_sample_positions_names.append(sample_position_name)
    print(
        f"Sample positions to be removed from the db and registry: {removed_sample_positions_names}"
    )

    sample_view.add_sample_positions_to_db(
        sample_positions=sample_positions, parent_device_name=None
    )
    # next add positions within devices
    for device in devices:  # prepend device name to device sample positions
        sample_view.add_sample_positions_to_db(
            sample_positions=device.sample_positions, parent_device_name=device.name
        )

    # print the alarm configuration
    alarm_config = AlabOSConfig().get("alarm", {})
    Alarm(**alarm_config).print_configuration()

    return (
        {
            "removed_devices_names": removed_devices_names,
            "removed_sample_positions_names": removed_sample_positions_names,
        }
        if return_removed_devices_and_sample_positions_names
        else True
    )
