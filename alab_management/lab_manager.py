import re
import time
from contextlib import contextmanager
from typing import Type, Dict, List, Optional, Union, Any, cast

from bson import ObjectId
from pydantic import root_validator
from pydantic.main import BaseModel

from .logger import DBLogger
from .device_view.device import BaseDevice
from .device_view.device_view import DeviceView, DevicesLock
from .sample_view.sample_view import SampleView, SamplePositionsLock, SamplePositionRequest


class ResourcesRequest(BaseModel):
    """
    This class is used to validate the resource request. Each request should have a format of
    [DeviceType: List of SamplePositionRequest]

    See Also:
        :py:class:`SamplePositionRequest <alab_management.sample_view.sample_view.SamplePositionRequest>`
    """
    __root__: Dict[Optional[Type[BaseDevice]], List[SamplePositionRequest]]

    @root_validator(pre=True, allow_reuse=True)
    def preprocess(cls, values):  # pylint: disable=no-self-use,no-self-argument
        values = values["__root__"]
        # if the sample position request is string, we will automatically add a number attribute = 1.
        values = {k: [SamplePositionRequest.from_str(v_) if isinstance(v_, str) else v_
                      for v_ in v] for k, v in values.items()}
        return {"__root__": values}


@contextmanager
def _resource_lock(devices_lock: DevicesLock, sample_positions_lock: SamplePositionsLock,
                   resource_request: Dict[Optional[Type[BaseDevice]], List[Dict[str, Any]]],
                   logger: DBLogger):
    """
    A context manager that releases the devices and the sample positions when they are no longer needed.

    This context manager is only supposed to be used internally, to create context manager and expose
    to the task definitions
    """
    if devices_lock.devices is None or sample_positions_lock.sample_positions is None:
        raise ValueError("Get empty devices_lock or sample_positions_lock")
    requested_sample_positions = {}
    flattened_sample_positions = cast(Dict[str, List[str]], sample_positions_lock.sample_positions)

    for device_type, device in devices_lock.devices.items():  # type: ignore
        device_name = device.name
        sample_position_requests = resource_request[device_type]
        requested_sample_positions[device_type] = {
            sample_position_request["prefix"]: flattened_sample_positions.pop(
                sample_position_request["prefix"].replace("$", device_name))
            for sample_position_request in sample_position_requests
        }
    if None in resource_request:
        requested_sample_positions[None] = {
            sample_position_request["prefix"]: flattened_sample_positions.pop(sample_position_request["prefix"])
            for sample_position_request in resource_request[None]
        }

    log_id = logger.system_log(level="DEBUG", log_data={
        "logged_by": "LabManager",
        "type": "AssignedResources",
        "resources_list": {k.__name__ if k else str(k): [v_["prefix"] for v_ in v]
                           for k, v in resource_request.items()},
        "devices": {device_type.__name__: device.name
                    for device_type, device in devices_lock.devices.items()},
        "sample_positions": sample_positions_lock.sample_positions,
    })

    assert len(flattened_sample_positions) == 0, "All the sample positions should have been popped out."
    yield devices_lock.devices, requested_sample_positions

    devices_lock.release()
    sample_positions_lock.release()
    logger.system_log(level="DEBUG", log_data={
        "logged_by": "LabManager",
        "type": "ReleaseResources",
        "assign_log_id": log_id,
    })


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
        self.logger = DBLogger(task_id=task_id)

    def request_resources(
            self,
            resource_request: Union[
                ResourcesRequest, Dict[Optional[Type[BaseDevice]], List[Union[Dict[str, Any], str]]]]
    ) -> _resource_lock:  # type: ignore
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
        if not isinstance(resource_request, ResourcesRequest):
            resource_request = ResourcesRequest(__root__=resource_request)
        resource_request_formatted = resource_request.dict()["__root__"]
        self.logger.system_log(level="DEBUG", log_data={
            "logged_by": self.__class__.__name__,
            "type": "StartRequestResources",
            "task_id": self.task_id,
            "resources_list": {k.__name__ if k else str(k): [v_["prefix"] for v_ in v]
                               for k, v in resource_request_formatted.items()}
        })
        while True:
            devices_lock = self._device_view.request_devices(task_id=self.task_id, device_types=[
                device_type for device_type in resource_request_formatted.keys()
                if device_type is not None
            ])

            try:
                parsed_sample_positions_request = []
                for device_type, device in devices_lock.devices.items():  # type: ignore
                    device_name = device.name
                    parsed_sample_positions_request.extend([
                        {**sample_position_request,
                         "prefix": re.sub(r"\$", device_name, sample_position_request["prefix"])}
                        for sample_position_request in resource_request_formatted[device_type]])

                if any("$" in sample_position_request["prefix"]
                       for sample_position_request in resource_request_formatted.get(None, [])):
                    raise ValueError("$ should not appear under `None`, which is actually not a device.")
                parsed_sample_positions_request.extend(resource_request_formatted.get(None, []))
                # wait for 10 minutes
                # if it is still not available, release it, wait for 1 minutes
                # and start to request devices again
                sample_positions_lock = self._sample_view.request_sample_positions(
                    task_id=self.task_id,
                    sample_positions=[SamplePositionRequest(**request) for request in parsed_sample_positions_request],
                    timeout=600
                )

                if sample_positions_lock is not None:
                    return _resource_lock(devices_lock=devices_lock,  # type: ignore
                                          sample_positions_lock=sample_positions_lock,
                                          resource_request=resource_request_formatted, logger=self.logger)
                devices_lock.release()
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
