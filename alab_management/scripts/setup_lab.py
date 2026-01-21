"""
Generate device, sample position, task definitions from user defined files (task & device)
and write them to MongoDB, which will make it easier to query.
"""

from alab_management.alarm import Alarm
from alab_management.config import AlabOSConfig
from alab_management.device_view.device import get_current_devices
from alab_management.sample_view.sample import (
    SamplePosition,
    get_current_standalone_sample_positions,
)


def _process_device_sample_positions(
    device_name,
    devices_sample_positions_before_reload,
    current_devices_sample_positions,
):
    """Process sample positions for a specific device."""
    removed_positions = []
    current_device_sample_positions = current_devices_sample_positions[device_name]
    current_sample_position_names = [
        pos.name for pos in current_device_sample_positions
    ]

    for sample_position in devices_sample_positions_before_reload[device_name]:
        if sample_position.name not in current_sample_position_names:
            removed_positions.append(sample_position)

    return removed_positions


def _find_removed_sample_positions_in_devices(
    devices_sample_positions_before_reload, current_devices_sample_positions
):
    """Find sample positions in devices that have been removed."""
    removed_sample_positions_in_devices = {}
    for device_name in devices_sample_positions_before_reload:
        for current_device_name in current_devices_sample_positions:
            if current_device_name == device_name:
                removed_positions = _process_device_sample_positions(
                    device_name,
                    devices_sample_positions_before_reload,
                    current_devices_sample_positions,
                )
                if removed_positions:
                    removed_sample_positions_in_devices[device_name] = removed_positions
    return removed_sample_positions_in_devices


def _process_device_sample_position_updates(
    device_name,
    devices_sample_positions_before_reload,
    current_devices_sample_positions,
):
    """Process sample position updates for a specific device."""
    updated_positions = []
    for sample_position in devices_sample_positions_before_reload[device_name]:
        for current_sample_position in current_devices_sample_positions[device_name]:
            if (
                sample_position.name == current_sample_position.name
                and sample_position.number != current_sample_position.number
            ):
                updated_positions.append(current_sample_position)
    return updated_positions


def _find_updated_sample_positions_in_devices(
    devices_sample_positions_before_reload, current_devices_sample_positions
):
    """Find sample positions in devices that have been updated."""
    updated_sample_positions_in_devices = {}
    for device_name in devices_sample_positions_before_reload:
        for current_device_name in current_devices_sample_positions:
            if current_device_name == device_name:
                updated_positions = _process_device_sample_position_updates(
                    device_name,
                    devices_sample_positions_before_reload,
                    current_devices_sample_positions,
                )
                if updated_positions:
                    updated_sample_positions_in_devices[device_name] = updated_positions
    return updated_sample_positions_in_devices


def setup_lab(
    reload: bool = False,
) -> (
    dict[str, list[str] | list[SamplePosition] | dict[str, list[SamplePosition]]] | bool
):
    """Setup the lab by adding devices and sample positions to the database.

    Args:
        reload (bool): If True, reload the definitions from the config file.

    Returns
    -------
        dict or bool: If reload is True, returns a dict with the changes made. Otherwise returns True.
    """
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

    # step 0: get all the devices and sample positions before reload to calculate the negative delta of sample positions numbers
    if reload:
        reset_current_device_registry()
        reset_current_standalone_sample_position_registry()
    devices_before_reload = get_all_devices().values()
    sample_positions_dict_before_reload = get_all_standalone_sample_positions()

    # Goal: calculate positive and negative delta of: devices, sample positions, and device sample positions.
    # Apply positive delta directly. Negative delta will be applied by device manager once the devices, sample positions,
    # and device sample positions are not used anymore.

    # step 1: load the definitions
    load_definition(reload=reload)

    # step 2: get all the devices from the __init__.py and the ones that are currently connected [current state]
    devices = (
        get_all_devices().values()
    )  # all device from the __init__.py and the ones that are currently connected
    device_dict = (
        get_all_devices()
    )  # all device from the __init__.py and the ones that are currently connected

    # step 3: get all the devices from the __init__.py during this setup (only equals to devices if not reload) [future state]
    current_devices = get_current_devices().values()
    current_devices_dict = (
        get_current_devices()
    )  # all device from the __init__.py during this setup (only equals to devices if not reload)
    all_available_devices = DeviceView().get_all()  # all device from the db
    available_devices_names = [
        device["name"] for device in all_available_devices
    ]  # all device names from the db

    # step 4: filter out the devices that are not in the db [positive delta of devices]
    filtered_devices = {}  # all device from the __init__.py that are not in the db
    for device_name, device in device_dict.items():
        if device_name not in available_devices_names:
            filtered_devices[device_name] = (
                device  # all device from the __init__.py that are not in the db
            )

    # step 5: filter out the devices that are not in the __init__.py
    # [negative delta of devices, will be applied by device manager once the devices are not used anymore]
    removed_devices_names = (
        []
    )  # all device names from the db that are not in the __init__.py
    for device_name in available_devices_names:
        if device_name not in current_devices_dict:
            removed_devices_names.append(device_name)
    print(f"Devices to be removed from the db and registry: {removed_devices_names}")

    # step 6: add the new devices to the db [apply positive delta of devices]
    DeviceView().add_devices_to_db(filtered_devices)
    for device_instance in filtered_devices.values():
        device_instance._apply_default_db_values()
        # trigger database updates for Device values stored within db. These are not executed upon instantiation
        # because the device documents were not yet created within the Device collection.
    print(f"Devices added to the db and registry: {filtered_devices}")

    # step 7: get all the standalone sample positions from the __init__.py
    # and the ones that are currently active in the lab [current state]
    sample_view = SampleView()
    # get the standalone sample positions in the registry
    # note that a SamplePosition object consist of a name and a number
    # where the number is the number of slots in the sample position
    mapped_sample_positions = get_all_standalone_sample_positions()
    sample_positions = list(
        mapped_sample_positions.values()
    )  # all sample positions from the __init__.py and the ones that are currently active in the lab
    # step 8: get all the standalone sample positions from the __init__.py during this setup [future state]
    mapped_current_sample_positions = get_current_standalone_sample_positions()
    current_sample_positions = list(
        mapped_current_sample_positions.values()
    )  # all sample positions from the __init__.py during this setup (only equals to sample_positions if not reload)
    sample_positions_names = [
        sample_position.name for sample_position in sample_positions
    ]
    current_sample_positions_names = [
        sample_position.name for sample_position in current_sample_positions
    ]

    # step 9: add new sample positions to the db [apply positive delta of prefix of sample positions]
    # do not need to worry about the sample positions that are already in the db
    # because the adding will only be done for new sample positions or slots within existing sample positions
    sample_view.add_sample_positions_to_db(
        sample_positions=sample_positions, parent_device_name=None
    )
    # TODO: calculate positive delta of sample positions to print out
    # step 10: remove prefix of sample positions names that are not in the lab anymore
    # [calculate negative delta of prefix of sample positions]
    removed_sample_positions_prefixes = []
    for sample_position_name in sample_positions_names:
        if sample_position_name not in current_sample_positions_names:
            removed_sample_positions_prefixes.append(sample_position_name)
    print(
        f"Standalone sample positions to be removed from the db and registry: {removed_sample_positions_prefixes}"
    )

    # step 11: find the current sample positions that has the same name but different number of slots
    # [calculate negative delta of sample positions numbers]
    # than the ones in the sample_positions
    sample_positions_before_reload = list(
        sample_positions_dict_before_reload.values()
    )  # all sample positions information not including __init__.py.
    # This is used to check if there is any negative delta of sample positions numbers
    sample_positions_names_before_reload = [
        sample_position.name for sample_position in sample_positions_before_reload
    ]
    updated_sample_positions = []
    for current_sample_position_name in current_sample_positions_names:
        try:
            if (
                current_sample_position_name in sample_positions_names_before_reload
                and (
                    sample_positions_dict_before_reload[
                        current_sample_position_name
                    ].number
                    != mapped_current_sample_positions[
                        current_sample_position_name
                    ].number
                )
            ):
                # if the sample position is in the sample_positions, but the number of slots is different,
                # then it is an updated sample position
                updated_sample_positions.append(
                    mapped_current_sample_positions[current_sample_position_name]
                )
        except KeyError:
            continue
    print(f"Updated standalone sample positions: {updated_sample_positions}")

    # step 12: add device sample positions to the db [apply positive delta of device prefix of sample positions]
    # next add positions within devices
    for device in devices:  # prepend device name to device sample positions
        sample_view.add_sample_positions_to_db(
            sample_positions=device.sample_positions, parent_device_name=device.name
        )

    # step 13: find the current sample positions in devices that are not in the db
    # [calculate negative delta of device sample positions]
    # positive is already handled in step 12, so we only need to calculate negative delta to be handled by device manager
    # once the devices are not used anymore
    devices_sample_positions_before_reload = {
        device.name: device.sample_positions for device in devices_before_reload
    }
    current_devices_sample_positions = {
        device.name: device.sample_positions for device in current_devices
    }
    removed_sample_positions_in_devices = _find_removed_sample_positions_in_devices(
        devices_sample_positions_before_reload, current_devices_sample_positions
    )
    print(f"Removed sample positions in devices: {removed_sample_positions_in_devices}")

    # step 14: check if there is any update of sample positions from the devices
    # [calculate negative delta of sample positions numbers]
    # positive is already handled in step 12, so we only need to calculate negative delta to be handled by device manager
    # once the devices are not used anymore
    updated_sample_positions_in_devices = _find_updated_sample_positions_in_devices(
        devices_sample_positions_before_reload, current_devices_sample_positions
    )
    print(f"Updated sample positions in devices: {updated_sample_positions_in_devices}")

    # print the alarm configuration
    alarm_config = AlabOSConfig().get("alarm", {})
    Alarm(**alarm_config).print_configuration()

    return (
        {
            "removed_devices_names": removed_devices_names,
            "updated_sample_positions": updated_sample_positions,
            "removed_sample_positions_prefixes": removed_sample_positions_prefixes,
            "updated_sample_positions_in_devices": updated_sample_positions_in_devices,
            "removed_sample_positions_in_devices": removed_sample_positions_in_devices,
        }
        if reload
        else True
    )
