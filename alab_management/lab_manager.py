import re
from contextlib import contextmanager
from typing import Type, Dict, List, Optional

from bson import ObjectId

from alab_management import BaseDevice
from alab_management.device_view import DeviceView
from alab_management.device_view.device_view import DevicesLock
from alab_management.sample_view import SampleView
from alab_management.sample_view.sample_view import SamplePositionsLock


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

    yield devices_lock.devices, requested_sample_positions

    devices_lock.release()
    sample_positions_lock.release()


class LabManager:
    def __init__(self, task_id: ObjectId, device_view: DeviceView, sample_view: SampleView):
        self.task_id = task_id
        self._device_view = device_view
        self._sample_view = sample_view

    def request_devices(self, timeout: Optional[int], *device_type: Type[BaseDevice]) -> DevicesLock:
        return self._device_view.request_devices(task_id=self.task_id, timeout=timeout, *device_type)

    def request_sample_positions(self, timeout: Optional[int], *sample_position: str) -> SamplePositionsLock:
        return self._sample_view.request_sample_positions(task_id=self.task_id, timeout=timeout, *sample_position)

    def request_resources(self, devices_and_sample_positions: Dict[Optional[Type[BaseDevice]], List[str]]) \
            -> resource_lock:
        while True:
            devices_lock = self.request_devices(*[device_type for device_type in devices_and_sample_positions.keys()
                                                  if device_type is not None])
            parsed_sample_positions = []
            for device_type, device in devices_lock.devices.items():
                device_name = device.name
                parsed_sample_positions.extend([re.sub(r"\$", device_name, sample_position)
                                                for sample_position in devices_and_sample_positions[device_type]])
            sample_positions_lock = self.request_sample_positions(timeout=600, *parsed_sample_positions)

            if sample_positions_lock is not None:
                return resource_lock(devices_lock=devices_lock, sample_positions_lock=sample_positions_lock,
                                     devices_and_sample_positions=devices_and_sample_positions)

    def get_sample(self, sample_id: ObjectId):
        return self._sample_view.get_sample(sample_id)

    def move_sample(self, sample_id: ObjectId, position: str):
        return self._sample_view.move_sample(sample_id=sample_id, position=position)
