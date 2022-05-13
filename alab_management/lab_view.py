"""
Each task process will have a ``LavView`` instance, through which it can request
the lab resources (devices and sample positions). It can also update the position
of a sample in the lab.
"""

from contextlib import contextmanager
from typing import Type, Dict, List, Optional, Union

from bson import ObjectId
from pydantic import root_validator
from pydantic.main import BaseModel

from .device_manager import DevicesClient
from .device_view.device import BaseDevice
from .logger import DBLogger
from .sample_view.sample_view import SampleView, SamplePositionRequest
from .task_manager import ResourceRequester


class DeviceRunningException(Exception):
    """
    Raise when a task try to release a device that is still running
    """


class ResourcesRequest(BaseModel):
    """
    This class is used to validate the resource request. Each request should have a format of
    [DeviceType: List of SamplePositionRequest]

    See Also:
        :py:class:`SamplePositionRequest <alab_management.sample_view.sample_view.SamplePositionRequest>`
    """
    __root__: Dict[Optional[Type[BaseDevice]], List[SamplePositionRequest]]  # type: ignore

    @root_validator(pre=True, allow_reuse=True)
    def preprocess(cls, values):  # pylint: disable=no-self-use,no-self-argument
        values = values["__root__"]
        # if the sample position request is string, we will automatically add a number attribute = 1.
        values = {k: [SamplePositionRequest.from_str(v_) if isinstance(v_, str) else v_
                      for v_ in v] for k, v in values.items()}
        return {"__root__": values}


class LabView:
    """
    LabView is a wrapper over device view and sample view.
    A task can get access to that to request resources, query sample and
    update sample positions.
    """

    def __init__(self, task_id: ObjectId):
        self._task_id = task_id
        self._sample_view = SampleView()
        self._resource_requester = ResourceRequester(task_id=task_id)
        self._device_client = DevicesClient(task_id=task_id, timeout=30)
        self.logger = DBLogger(task_id=task_id)

    @property
    def task_id(self) -> ObjectId:
        return self._task_id

    @contextmanager
    def request_resources(
            self,
            resource_request: Dict[Optional[Type[BaseDevice]], List[Union[Dict[str, Union[str, int]], str]]],
            timeout: Optional[float] = None,
    ):
        """
        Request devices and sample positions. This function is a context manager, which should be used in
        a with statement to ensure all the devices are released when the task is done.

        Usually, devices_and_sample_positions has the format {DeviceType: ["sample_position_1", ...]}. The
        DeviceType can be ``None`` so that you can request the sample positions that do not belong to
        any devices (in principle, you can put all the sample positions under one device type)

        If you want to request multiple sample positions with the same prefix, you can instead replace the name of
        sample position name with a dict {"prefix": <str>, "number": <int>}

        Note that the sample position name will try to find available sample positions that start with this
        specified name prefix.

        And since sometimes you can only know which device you will use until you request the device,
        you can use ``$`` to represent the name of device, e.g. {Furnace: ["$/inside"]} will be parsed to
        ``furnace_1/inside`` if we are assigned to a furnace named ``furnace_1``.
        """
        result = self._resource_requester.request_resources(resource_request=resource_request,
                                                            timeout=timeout)
        devices = result["devices"]
        sample_positions = result["sample_positions"]
        request_id = result["request_id"]
        devices = {device_type: self._device_client.create_device_wrapper(device_name)
                   for device_type, device_name in devices.items()}  # type: ignore
        yield devices, sample_positions

        self._resource_requester.release_resources(request_id=request_id)

    def get_sample(self, sample_id: ObjectId):
        """
        Get a sample by id, see also
        :py:meth:`get_sample <alab_management.sample_view.sample_view.SampleView.get_sample>`
        """
        return self._sample_view.get_sample(sample_id)

    def move_sample(self, sample_id: ObjectId, position: Optional[str]):
        """
        Move a sample to a new position, see also
        :py:meth:`move_sample <alab_management.sample_view.sample_view.SampleView.move_sample>`
        """
        # check if this sample position is locked by current task
        if position is not None and self._sample_view.get_sample_position_status(position)[1] != self._task_id:
            raise ValueError(f"Cannot move sample to a sample position ({position}) without locking it.")

        # check if this sample is owned by current task
        sample = self._sample_view.get_sample(sample_id=sample_id)
        if sample is not None and sample.task_id != self._task_id:
            raise ValueError("Cannot move a sample that is not belong to this task.")

        return self._sample_view.move_sample(sample_id=sample_id, position=position)

    def get_locked_sample_positions(self) -> List[str]:
        """
        Get a list of sample positions that are occupied by this task
        """
        return self._sample_view.get_sample_positions_by_task(task_id=self._task_id)
