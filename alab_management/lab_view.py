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

from alab_management.device_manager import DevicesClient
from alab_management.device_view.device import BaseDevice
from alab_management.logger import DBLogger
from alab_management.sample_view.sample_view import SampleView, SamplePositionRequest
from alab_management.task_manager import ResourceRequester


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
        values = {
            k: [
                SamplePositionRequest.from_str(v_) if isinstance(v_, str) else v_
                for v_ in v
            ]
            for k, v in values.items()
        }
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
        resource_request: Dict[
            Optional[Union[Type[BaseDevice], str]], Dict[str, Union[str, int]]
        ],
        priority: Optional[int] = None,
        timeout: Optional[float] = None,
    ):
        """
        Request devices and sample positions. This function is a context manager, which should be used in
        a with statement to ensure all the devices are released when the task is done.

        resource_request format is:
            {device: {position: number, ...}, ...}
        device can be a name of a specific device (str), a type of device, or None. If device is a type, the resource request will look for any available device of that type. If device is None, the resource request will look for sample positions that do not belong to a device.
        position is the name of a sample position that should be reserved on the device, and number is the number of such positions that should be reserved. If the device is required but no positions are required, this can be left as an empty dictionary.

        Examples:

        {TubeFurnace: {"tray": 4}, "arm1": {}} will find the first available TubeFurnace device, then reserve 4 sample positions of "{tubefurnacename}/tray/{tray_index}" on that device. It will also find the device named "arm1".


        The priority of the request can optionally be specified as a positive integer, which should probably be in the range of 0-40. 20 is the default "NORMAL" priority level. Higher number = higher priority. Numbers >= 100 are reserved for urgent/error correcting requests.
        """
        result = self._resource_requester.request_resources(
            resource_request=resource_request, timeout=timeout, priority=priority
        )
        devices = result["devices"]
        sample_positions = result["sample_positions"]
        request_id = result["request_id"]
        devices = {
            device_type: self._device_client.create_device_wrapper(device_name)
            for device_type, device_name in devices.items()
        }  # type: ignore
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
        if (
            position is not None
            and self._sample_view.get_sample_position_status(position)[1]
            != self._task_id
        ):
            raise ValueError(
                f"Cannot move sample to a sample position ({position}) without locking it."
            )

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
