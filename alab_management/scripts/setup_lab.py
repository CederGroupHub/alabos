"""
Generate device, sample position, task definitions from user defined files (task & device)
and write them to MongoDB, which will make it easier to query.
"""

import logging

from alab_management.alarm import Alarm
from alab_management.config import AlabOSConfig
from alab_management.device_view.device import get_current_devices
from alab_management.sample_view.sample import (
    SamplePosition,
    get_current_standalone_sample_positions,
)

logger = logging.getLogger(__name__)


def _format_sample_positions(positions: list[SamplePosition]) -> list[str]:
    return [f"{position.name}({position.number})" for position in positions]


def _format_device_sample_positions(
    positions_by_device: dict[str, list[SamplePosition]],
) -> dict[str, list[str]]:
    return {
        device_name: _format_sample_positions(positions)
        for device_name, positions in positions_by_device.items()
    }


def _process_device_sample_positions(
    device_name,
    devices_sample_positions_before,
    current_devices_sample_positions,
):
    """Process sample positions for a specific device."""
    removed_positions = []
    current_device_sample_positions = current_devices_sample_positions[device_name]
    current_sample_position_names = [
        pos.name for pos in current_device_sample_positions
    ]

    for sample_position in devices_sample_positions_before[device_name]:
        if sample_position.name not in current_sample_position_names:
            removed_positions.append(sample_position)

    return removed_positions


def _find_removed_sample_positions_in_devices(
    devices_sample_positions_before, current_devices_sample_positions
):
    """Find sample positions in devices that have been removed."""
    removed_sample_positions_in_devices = {}
    for device_name in devices_sample_positions_before:
        for current_device_name in current_devices_sample_positions:
            if current_device_name == device_name:
                removed_positions = _process_device_sample_positions(
                    device_name,
                    devices_sample_positions_before,
                    current_devices_sample_positions,
                )
                if removed_positions:
                    removed_sample_positions_in_devices[device_name] = removed_positions
    return removed_sample_positions_in_devices


def _process_device_sample_position_updates(
    device_name,
    devices_sample_positions_before,
    current_devices_sample_positions,
):
    """Process sample position updates for a specific device."""
    updated_positions = []
    for sample_position in devices_sample_positions_before[device_name]:
        for current_sample_position in current_devices_sample_positions[device_name]:
            if (
                sample_position.name == current_sample_position.name
                and sample_position.number != current_sample_position.number
            ):
                updated_positions.append(current_sample_position)
    return updated_positions


def _find_updated_sample_positions_in_devices(
    devices_sample_positions_before, current_devices_sample_positions
):
    """Find sample positions in devices that have been updated."""
    updated_sample_positions_in_devices = {}
    for device_name in devices_sample_positions_before:
        for current_device_name in current_devices_sample_positions:
            if current_device_name == device_name:
                updated_positions = _process_device_sample_position_updates(
                    device_name,
                    devices_sample_positions_before,
                    current_devices_sample_positions,
                )
                if updated_positions:
                    updated_sample_positions_in_devices[device_name] = updated_positions
    return updated_sample_positions_in_devices


def setup_lab() -> bool:
    """Setup the lab by adding devices and sample positions to the database.

    Returns
    -------
        True on success.
    """
    from alab_management.device_view import (
        DeviceView,
        get_all_devices,
    )
    from alab_management.sample_view import SampleView
    from alab_management.sample_view.sample import get_all_standalone_sample_positions
    from alab_management.utils.module_ops import load_definition

    devices_before = get_all_devices().values()
    sample_positions_dict_before = get_all_standalone_sample_positions()

    load_definition()

    devices = get_all_devices().values()
    device_dict = get_all_devices()
    current_devices = get_current_devices().values()
    current_devices_dict = get_current_devices()
    all_available_devices = DeviceView().get_all()
    available_devices_names = [device["name"] for device in all_available_devices]

    filtered_devices = {}
    for device_name, device in device_dict.items():
        if device_name not in available_devices_names:
            filtered_devices[device_name] = device

    removed_devices_names = []
    for device_name in available_devices_names:
        if device_name not in current_devices_dict:
            removed_devices_names.append(device_name)
    logger.info(f'Devices to be removed from the db and registry: {removed_devices_names}')

    DeviceView().add_devices_to_db(filtered_devices)
    for device_instance in filtered_devices.values():
        device_instance._apply_default_db_values()
    logger.info(
        "Devices added to the db and registry: %s",
        sorted(filtered_devices.keys()),
    )

    DeviceView().sync_device_definitions(device_dict)

    for device_name, device_instance in device_dict.items():
        try:
            device_instance._apply_default_db_values()
        except Exception as error:  # noqa: BLE001 - one bad device must not stop setup
            logger.error(f'Could not apply default attribute values for {device_name}: {error}')

    sample_view = SampleView()
    mapped_sample_positions = get_all_standalone_sample_positions()
    sample_positions = list(mapped_sample_positions.values())
    mapped_current_sample_positions = get_current_standalone_sample_positions()
    current_sample_positions = list(mapped_current_sample_positions.values())
    sample_positions_names = [
        sample_position.name for sample_position in sample_positions
    ]
    current_sample_positions_names = [
        sample_position.name for sample_position in current_sample_positions
    ]

    sample_view.add_sample_positions_to_db(
        sample_positions=sample_positions, parent_device_name=None
    )
    removed_sample_positions_prefixes = []
    for sample_position_name in sample_positions_names:
        if sample_position_name not in current_sample_positions_names:
            removed_sample_positions_prefixes.append(sample_position_name)
    logger.info(f'Standalone sample positions to be removed from the db and registry: {removed_sample_positions_prefixes}')

    sample_positions_before = list(sample_positions_dict_before.values())
    sample_positions_names_before = [
        sample_position.name for sample_position in sample_positions_before
    ]
    updated_sample_positions = []
    for current_sample_position_name in current_sample_positions_names:
        try:
            if (
                current_sample_position_name in sample_positions_names_before
                and (
                    sample_positions_dict_before[
                        current_sample_position_name
                    ].number
                    != mapped_current_sample_positions[
                        current_sample_position_name
                    ].number
                )
            ):
                updated_sample_positions.append(
                    mapped_current_sample_positions[current_sample_position_name]
                )
        except KeyError:
            continue
    logger.info(
        "Updated standalone sample positions: %s",
        _format_sample_positions(updated_sample_positions),
    )

    for device in devices:
        sample_view.add_sample_positions_to_db(
            sample_positions=device.sample_positions, parent_device_name=device.name
        )

    devices_sample_positions_before = {
        device.name: device.sample_positions for device in devices_before
    }
    current_devices_sample_positions = {
        device.name: device.sample_positions for device in current_devices
    }
    removed_sample_positions_in_devices = _find_removed_sample_positions_in_devices(
        devices_sample_positions_before, current_devices_sample_positions
    )
    logger.info(
        "Removed sample positions in devices: %s",
        _format_device_sample_positions(removed_sample_positions_in_devices),
    )

    updated_sample_positions_in_devices = _find_updated_sample_positions_in_devices(
        devices_sample_positions_before, current_devices_sample_positions
    )
    logger.info(
        "Updated sample positions in devices: %s",
        _format_device_sample_positions(updated_sample_positions_in_devices),
    )

    alarm_config = AlabOSConfig().get("alarm", {})
    Alarm(**alarm_config).print_configuration()

    return True
