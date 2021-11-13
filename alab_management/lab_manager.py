import re
import time
from contextlib import contextmanager
from typing import Type, Dict, List, Optional

from bson import ObjectId

from .device_view.device import BaseDevice
from .device_view.device_view import DeviceView, DevicesLock
from .sample_view.sample_view import SampleView, SamplePositionsLock


@contextmanager
def resource_lock(devices_lock: DevicesLock, sample_positions_lock: SamplePositionsLock,
                  devices_and_sample_positions: Dict[Optional[Type[BaseDevice]], List[str]]):
    """
    A context manager that releases the devices and the sample positions when they are no longer needed.
    """
    requested_sample_positions = {}
    flattened_sample_positions = sample_positions_lock.sample_positions.copy()  # type: ignore

    for device_type, device in devices_lock.devices.items():  # type: ignore
        device_name = device.name
        sample_positions_prefixes = devices_and_sample_positions[device_type]
        requested_sample_positions[device_type] = {
            sample_positions_prefix: flattened_sample_positions.pop(sample_positions_prefix.replace("$", device_name))
            for sample_positions_prefix in sample_positions_prefixes
        }
    if None in devices_and_sample_positions:
        requested_sample_positions[None] = {
            sample_positions: flattened_sample_positions.pop(sample_positions)
            for sample_positions in devices_and_sample_positions[None]
        }
    yield devices_lock.devices, requested_sample_positions

    devices_lock.release()
    sample_positions_lock.release()


class LabManager:
    """
    LabManager is a wrapper over device view and sample view.
    A task can get access to that to request resources, query sample and
    update sample positions.
    """
    def __init__(self, task_id: ObjectId, device_view: DeviceView, sample_view: SampleView):
        self.task_id = task_id
        self._device_view = device_view
        self._sample_view = sample_view

    def request_devices(self, device_types: List[Type[BaseDevice]], timeout: Optional[int] = None) -> DevicesLock:
        """
        Request devices, see also
        :py:meth:`request_devices <alab_management.device_view.device_view.DeviceView.request_devices>`
        """
        return self._device_view.request_devices(self.task_id, device_types, timeout=timeout)

    def request_sample_positions(self, sample_positions: List[str], timeout: Optional[int] = None) \
            -> SamplePositionsLock:
        """
        Request sample positions, see also
        :py:meth:`request_sample_positions <alab_management.sample_view.sample_view.SampleView.request_sample_positions>`  # noqa pylint: disable=line-too-long
        """
        return self._sample_view.request_sample_positions(self.task_id, sample_positions, timeout=timeout)

    def request_resources(self, devices_and_sample_positions: Dict[Optional[Type[BaseDevice]], List[str]]) \
            -> resource_lock:  # type: ignore
        """
        Request devices and sample positions

        Usually, devices_and_sample_positions has the format {DeviceType: ["sample_position_1", ...]}. The
        DeviceType can be ``None`` so that you can request the sample positions that do not belong to
        any devices (for readability, in principal you can put all the sample positions under one device type)

        Note that the sample position name will try to find available sample positions that start with this
        specified name prefix.

        And since sometimes you can only know which device you will use until you request the device,
        you can use ``$`` to represent the name of device, e.g. {Furnace: ["$.inside"]} will be parsed to
        ``furnace_1.inside`` if we are assigned to a furnace named ``furnace_1``.
        """
        while True:
            devices_lock = self.request_devices([
                device_type for device_type in devices_and_sample_positions.keys()
                if device_type is not None
            ])

            try:
                parsed_sample_positions = []
                for device_type, device in devices_lock.devices.items():  # type: ignore
                    device_name = device.name
                    parsed_sample_positions.extend([re.sub(r"\$", device_name, sample_position)
                                                    for sample_position in devices_and_sample_positions[device_type]])

                if any("$" in sample_position_prefix
                       for sample_position_prefix in devices_and_sample_positions.get(None, [])):
                    raise ValueError("$ should not appear under `None`, which is actually not a device.")
                parsed_sample_positions.extend(devices_and_sample_positions.get(None, []))
                # wait for 10 minutes
                # if it is still not available, release it, wait for 1 minutes
                # and start to request devices again
                sample_positions_lock = self.request_sample_positions(timeout=600,
                                                                      sample_positions=parsed_sample_positions)

                if sample_positions_lock is not None:
                    return resource_lock(devices_lock=devices_lock,  # type: ignore
                                         sample_positions_lock=sample_positions_lock,
                                         devices_and_sample_positions=devices_and_sample_positions)
            except Exception:
                devices_lock.release()
                raise

            time.sleep(60)

    def get_sample(self, sample_id: ObjectId):
        """
        Get a sample by id, see also
        :py:meth:`get_sample <alab_management.sample_view.sample_view.SampleView.get_sample>`
        """
        return self._sample_view.get_sample(sample_id)

    def move_sample(self, sample_id: ObjectId, position: str):
        """
        Move a sample to a new position, see also
        :py:meth:`move_sample <alab_management.sample_view.sample_view.SampleView.move_sample>`
        """
        return self._sample_view.move_sample(sample_id=sample_id, position=position)
