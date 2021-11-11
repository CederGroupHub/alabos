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
    requested_sample_positions = {}
    flattened_sample_positions = sample_positions_lock.sample_positions.copy()

    for device_type, device in devices_lock.devices.items():
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
        :py:meth:`request_sample_positions <alab_management.sample_view.sample_view.SampleView.request_sample_positions>`
        """
        return self._sample_view.request_sample_positions(self.task_id, sample_positions, timeout=timeout)

    def request_resources(self, devices_and_sample_positions: Dict[Optional[Type[BaseDevice]], List[str]]) \
            -> resource_lock:
        while True:
            devices_lock = self.request_devices([device_type for device_type in devices_and_sample_positions.keys()
                                                 if device_type is not None])

            try:
                parsed_sample_positions = []
                for device_type, device in devices_lock.devices.items():
                    device_name = device.name
                    parsed_sample_positions.extend([re.sub(r"\$", device_name, sample_position)
                                                    for sample_position in devices_and_sample_positions[device_type]])
                parsed_sample_positions.extend(devices_and_sample_positions.get(None, []))
                # wait for 10 minutes
                # if it is still not available, release it, wait for 1 minutes
                # and start to request devices again
                sample_positions_lock = self.request_sample_positions(timeout=600,
                                                                      sample_positions=parsed_sample_positions)

                if sample_positions_lock is not None:
                    return resource_lock(devices_lock=devices_lock, sample_positions_lock=sample_positions_lock,
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
