"""
This module is adapted from https://github.com/Mause/rpc.

The task process can only get access to a wrapper over the real device object. The wrapper will
redirect all the method calls to the real device object via RabbitMQ. The real device object is in
DeviceManager class, which will handle all the request to run certain methods on the real device.
"""

import logging

logger = logging.getLogger(__name__)
import time
from collections.abc import Callable
from concurrent.futures import Future, TimeoutError as FuturesTimeoutError
from contextlib import contextmanager
from enum import Enum, auto
from functools import partial
from threading import Thread
from typing import Any, NoReturn, cast
from unittest.mock import Mock
from uuid import uuid4

import dill
import pika
from bson import ObjectId
from pika import BasicProperties
from pika.adapters.blocking_connection import BlockingChannel
from pika.spec import Basic

from alab_management.sample_view.sample_view import SamplePositionStatus
from alab_management.scripts.setup_lab import setup_lab
from alab_management.utils.device_verbose_logging import (
    emit_device_trace,
    should_trace_device,
)
from alab_management.utils.logger import (
    DEVICE_RPC_HEARTBEAT_SECONDS,
    is_device_rpc_debug_enabled,
)

from .config import AlabOSConfig
from .device_view.device_view import DevicePauseStatus, DeviceTaskStatus, DeviceView
from .sample_view import SampleView
from .utils.data_objects import get_rabbitmq_connection
from .utils.module_ops import load_definition

DEFAULT_SERVER_QUEUE_SUFFIX = ".device_rpc"
DEFAULT_CLIENT_QUEUE_SUFFIX = DEFAULT_SERVER_QUEUE_SUFFIX + ".reply_to"


class DeviceManagerUnavailableError(RuntimeError):
    """Raised when a device call cannot reach the Device Manager at all."""


def _summarize_rpc_value(value: Any, *, max_len: int = 80) -> str:
    text = repr(value)
    if len(text) > max_len:
        return f"{text[: max_len - 3]}..."
    return text


def _summarize_rpc_call(*args: Any, **kwargs: Any) -> str:
    parts = [_summarize_rpc_value(arg) for arg in args[:3]]
    if len(args) > 3:
        parts.append(f"...+{len(args) - 3} args")
    for index, (key, value) in enumerate(kwargs.items()):
        if index >= 5:
            parts.append("...")
            break
        parts.append(f"{key}={_summarize_rpc_value(value)}")
    return ", ".join(parts) if parts else "-"


def _rpc_trace(device_name: str, message: str, *args: Any) -> None:
    if should_trace_device(device_name):
        emit_device_trace(device_name, message, *args)


def _rpc_trace_any_verbose(message: str, *args: Any) -> None:
    """Write an RPC breadcrumb for every currently verbose-traced device.

    Used for Device Manager consumer lifecycle events that are not yet tied to one device
    (e.g. "listening on queue X"), so the per-device verbose log still shows whether the
    consumer is alive.
    """
    from alab_management.utils.device_verbose_logging import get_verbose_devices

    devices = get_verbose_devices()
    if not devices:
        try:
            from alab_management.device_view.device_view import DeviceView

            devices = {device["name"] for device in DeviceView().get_all()}
        except Exception:
            devices = set()
    if not devices:
        if is_device_rpc_debug_enabled():
            logger.info("[device-rpc] " + (message % args if args else message))
        return
    for device_name in sorted(devices):
        emit_device_trace(device_name, message, *args)


class MethodCallStatus(Enum):
    """The status of a method call."""

    PENDING = auto()
    IN_PROGRESS = auto()
    SUCCESS = auto()
    FAILURE = auto()


class DeviceMethodCallState:
    """holds the status of a pending method call to a device."""

    status: MethodCallStatus
    future: Future
    last_updated: float


class DeviceWrapper:
    """A wrapper over the device."""

    class DeviceMethodWrapper:
        """A wrapper over a device method."""

        def __init__(self, device_name: str, method: str, method_handler: Callable):
            self._device_name = device_name
            self._method: str = method
            self._method_handler = method_handler

        @property
        def method(self) -> str:
            """The name of the method."""
            return self._method

        def __call__(self, *args, **kwargs):
            """Call the method."""
            return self._method_handler(*args, **kwargs)

        def __repr__(self) -> str:
            """Return the representation of the method."""
            return f"<method {self._device_name}.{self._method}>"

        def _raise(self, *args, **kwargs) -> NoReturn:  # pylint: disable=no-self-use
            """Raise an error."""
            raise AttributeError(
                "This is a class method, you cannot use it as an attribute."
            )

        __str__ = __repr__

        __len__ = __getattr__ = __getitem__ = __add__ = __sub__ = __eq__ = __lt__ = (
            __gt__
        ) = _raise

    def __init__(self, name: str, devices_client: "DevicesClient"):
        self._name = name
        self._devices_client = devices_client

    @property
    def name(self) -> str:
        """The name of the device."""
        return self._name

    def __getattr__(self, method: str):
        """Get the method."""
        return self.DeviceMethodWrapper(
            device_name=self.name,
            method=method,
            method_handler=partial(self._devices_client.call, self.name, method),
        )


class DeviceManager:
    """
    Device manager is basically a rabbitmq-backed RPC server, which receives and
    executes commands on the device drivers, as requested by the task process.
    """

    def __init__(self, _check_status: bool = True):
        """
        Args:
            _check_status: Check if the task currently occupied this device when
              running commands. (disable it only for test purpose).
        """
        load_definition()
        self.sim_mode_flag = AlabOSConfig().is_sim_mode()
        if self.sim_mode_flag:
            self._rpc_queue_name = (
                AlabOSConfig()["general"]["name"] + "_sim" + DEFAULT_SERVER_QUEUE_SUFFIX
            )
        else:
            self._rpc_queue_name = (
                AlabOSConfig()["general"]["name"] + DEFAULT_SERVER_QUEUE_SUFFIX
            )
        self._device_view = DeviceView(connect_to_devices=True)
        self._sample_view = SampleView()
        self._check_status = _check_status
        self.threads = []

        self.device_names_to_be_removed = []
        self.device_names_to_be_removed_that_is_paused = []
        self.device_names_to_be_removed_thread = Thread(
            target=self._check_device_status_and_remove_if_not_occupied
        )
        self.device_names_to_be_removed_thread.daemon = True
        self.device_names_to_be_removed_thread.start()

        self.sample_positions_objects_to_be_updated = (
            []
        )  # this will be pooled by a list of sample positions objects
        self.sample_positions_prefixes_to_be_removed = (
            []
        )  # this will be pooled by a list of sample positions prefixes, that is corresponding to SamplePosition.name
        # (e.g., "Filled_vial_rack"), not the full name (Filled_vial_rack/1)
        self.sample_positions_in_devices_to_be_updated = (
            []
        )  # this will be pooled by a dict[str,SamplePosition] where the key is the device name
        # and the value is a list of sample position objects
        self.sample_positions_in_devices_to_be_updated_that_is_paused = (
            []
        )  # this will be pooled by a dict[str,SamplePosition] where the key is the device name
        # and the value is the sample position object
        self.sample_positions_in_devices_to_be_removed = (
            []
        )  # this will be pooled by a dict[str,SamplePosition] where the key is the device name
        # and the value is the sample position object
        self.sample_positions_in_devices_to_be_removed_that_is_paused = (
            []
        )  # this will be pooled by a dict[str,SamplePosition] where the key is the device name
        # and the value is the sample position object
        self.sample_positions_to_be_updated_or_removed_thread = Thread(
            target=self._check_sample_positions_status_and_update_or_remove_if_not_occupied
        )
        self.sample_positions_to_be_updated_or_removed_thread.daemon = True
        self.sample_positions_to_be_updated_or_removed_thread.start()

    def refresh_devices(self):
        """Re-connect the devices in the device view."""
        self._device_view.close()
        # call alabos setup_lab to refresh the devices and standalone sample positions
        logger.info('Installing new devices and sample positions. Adding discrepancies to the watchers for deletion once unoccupied.')
        update_and_removal_todo = setup_lab(reload=True)
        for device_name in update_and_removal_todo["removed_devices_names"]:
            if device_name not in self.device_names_to_be_removed:
                self.device_names_to_be_removed.append(device_name)
        for updated_sample_position in update_and_removal_todo[
            "updated_sample_positions"
        ]:
            if (
                updated_sample_position
                not in self.sample_positions_objects_to_be_updated
            ):
                self.sample_positions_objects_to_be_updated.append(
                    updated_sample_position
                )
        for removed_sample_position_prefix in update_and_removal_todo[
            "removed_sample_positions_prefixes"
        ]:
            if (
                removed_sample_position_prefix
                not in self.sample_positions_prefixes_to_be_removed
            ):
                self.sample_positions_prefixes_to_be_removed.append(
                    removed_sample_position_prefix
                )
        if (
            update_and_removal_todo["updated_sample_positions_in_devices"]
            not in self.sample_positions_in_devices_to_be_updated
        ):
            self.sample_positions_in_devices_to_be_updated.append(
                update_and_removal_todo["updated_sample_positions_in_devices"]
            )
        if (
            update_and_removal_todo["removed_sample_positions_in_devices"]
            not in self.sample_positions_in_devices_to_be_removed
        ):
            self.sample_positions_in_devices_to_be_removed.append(
                update_and_removal_todo["removed_sample_positions_in_devices"]
            )
        logger.info('Connecting to devices again...')
        self._device_view = DeviceView(
            connect_to_devices=True
        )  # create a new device view

    def _check_device_status_and_remove_if_not_occupied(self):
        """Check devices status and remove them if they are not occupied."""
        while True:
            time.sleep(5)
            for device_name in self.device_names_to_be_removed:
                device_entry: dict[str, Any] | None = self._device_view.get_device(
                    device_name
                )
                # check if the device is not occupied, and sample positions that are related to the device are also not occupied
                if device_entry[
                    "status"
                ] == DeviceTaskStatus.IDLE.name and not self._sample_view.get_samples_on_device(
                    device_name
                ):
                    logger.info(f'Device {device_name} is not occupied and has no samples on it, pausing it and then removing it from the device view.')
                    self._device_view.pause_device(device_name)
                    self.device_names_to_be_removed_that_is_paused.append(device_name)
                    self.device_names_to_be_removed.remove(device_name)
                    logger.info(f'Device {device_name} has been paused and will be removed from the device view after 10 seconds.')
                elif device_entry["status"] == DeviceTaskStatus.OCCUPIED.name:
                    logger.info(f'Device {device_name} is occupied, skipping and waiting for it to be unoccupied.')
                else:
                    logger.info(f"Device {device_name} is in status {device_entry['status']}, skipping and waiting for it to be unoccupied.")
            for device_name in self.device_names_to_be_removed_that_is_paused:
                device_entry: dict[str, Any] | None = self._device_view.get_device(
                    device_name
                )
                if (
                    device_entry["status"] == DeviceTaskStatus.IDLE.name
                    and device_entry["pause_status"] == DevicePauseStatus.PAUSED.name
                    and not self._sample_view.get_samples_on_device(device_name)
                ):
                    logger.info(f'Device {device_name} is not occupied, paused, and has no samples on it, removing it from the device view.')
                    self._device_view.remove_device(device_name)
                    # also remove the sample positions that are related to the device
                    self._sample_view.remove_sample_position_by_prefix(device_name)
                    self.device_names_to_be_removed_that_is_paused.remove(device_name)
                    logger.info(f'Device {device_name} has been removed from the device view.')
                elif device_entry["status"] == DeviceTaskStatus.OCCUPIED.name:
                    logger.info(f'Device {device_name} is occupied, skipping and waiting for it to be unoccupied.')
                    self._device_view.pause_device(device_name)
                else:
                    logger.info(f"Device {device_name} is in status {device_entry['status']}, skipping and waiting for it to be unoccupied.")
                    self._device_view.pause_device(device_name)

    def _get_sample_positions_status(self, sample_positions_names):
        """Get the status of sample positions."""
        sample_positions_status = []
        for sample_position_name in sample_positions_names:
            sample_positions_status.append(
                self._sample_view.get_sample_position_status(sample_position_name)[0]
            )
        return sample_positions_status

    def _handle_sample_position_update(self, sample_position_object):
        """Handle updating a sample position."""
        prefix = sample_position_object.name
        sample_positions_full_names = (
            self._sample_view.get_sample_positions_names_by_prefix(prefix)
        )
        sample_positions_status = self._get_sample_positions_status(
            sample_positions_full_names
        )

        if all(
            status == SamplePositionStatus.EMPTY for status in sample_positions_status
        ):
            logger.info(f'Sample position with prefix {prefix} is empty, removing it from the sample view and                 adding it back with the new number of slots.')
            self._sample_view.remove_sample_position_by_prefix(prefix)
            self._sample_view.add_sample_positions_to_db(
                sample_positions=[sample_position_object],
                parent_device_name=None,
            )
            self.sample_positions_objects_to_be_updated.remove(sample_position_object)
            logger.info(f'Sample position with prefix {prefix} has been updated in the sample view.')
        else:
            logger.info(f'Sample position with prefix {prefix} is not empty, current status of some sample positions: {sample_positions_status},skipping and waiting for it to be empty.')

    def _handle_sample_position_removal(self, prefix):
        """Handle removing a sample position."""
        sample_positions_full_names = (
            self._sample_view.get_sample_positions_names_by_prefix(prefix)
        )
        sample_positions_status = self._get_sample_positions_status(
            sample_positions_full_names
        )

        if all(
            status == SamplePositionStatus.EMPTY for status in sample_positions_status
        ):
            logger.info(f'Sample position with prefix {prefix} is empty, removing it from the sample view.')
            self._sample_view.remove_sample_position_by_prefix(prefix)
            self.sample_positions_prefixes_to_be_removed.remove(prefix)
            logger.info(f'Sample position with prefix {prefix} has been removed from the sample view.')
        else:
            logger.info(f'Sample position with prefix {prefix} is not empty, current status of some sample positions: {sample_positions_status}, skipping and waiting for it to be empty.')

    def _handle_device_sample_position_update(self, device_sample_position_dict):
        """Handle updating sample positions in devices."""
        processed = False
        for device_name in list(device_sample_position_dict.keys()):
            sample_positions_names_in_device = (
                self._sample_view.get_sample_positions_names_by_device(device_name)
            )
            sample_positions_status = self._get_sample_positions_status(
                sample_positions_names_in_device
            )

            if all(
                status == SamplePositionStatus.EMPTY
                for status in sample_positions_status
            ):
                device_entry: dict[str, Any] | None = self._device_view.get_device(
                    device_name
                )

                if device_entry["status"] == DeviceTaskStatus.IDLE.name:
                    logger.info(f'Device {device_name} is not occupied and has no samples on it, pausing it to update the sample positions.')
                    self._device_view.pause_device(device_name)
                    self.sample_positions_in_devices_to_be_updated_that_is_paused.append(
                        device_sample_position_dict
                    )
                    processed = True
                    logger.info(f'Device {device_name} has been paused to update the sample positions.')
                elif device_entry["status"] == DeviceTaskStatus.OCCUPIED.name:
                    logger.info(f'Device {device_name} is occupied, skipping and waiting for it to be unoccupied.')
                    self._device_view.pause_device(device_name)
                else:
                    logger.info(f"Device {device_name} is in status {device_entry['status']}, skipping and waiting for it to be unoccupied.")

        if processed:
            self.sample_positions_in_devices_to_be_updated.remove(
                device_sample_position_dict
            )

    def _handle_device_sample_position_update_paused(self, device_sample_position_dict):
        """Handle updating sample positions in paused devices."""
        processed = False
        for device_name in list(device_sample_position_dict.keys()):
            sample_positions_names_in_device = (
                self._sample_view.get_sample_positions_names_by_device(device_name)
            )
            sample_positions_status = self._get_sample_positions_status(
                sample_positions_names_in_device
            )

            if all(
                status == SamplePositionStatus.EMPTY
                for status in sample_positions_status
            ):
                device_entry = self._device_view.get_device(device_name)

                if (
                    device_entry["status"] == DeviceTaskStatus.IDLE.name
                    and device_entry["pause_status"] == DevicePauseStatus.PAUSED.name
                ):
                    logger.info(f'Device {device_name} is not occupied, paused, and has no samples on it, updating the sample positions.')
                    for sample_position_object in device_sample_position_dict[
                        device_name
                    ]:
                        self._sample_view.remove_sample_position_by_prefix(
                            f"{device_name}{sample_position_object.SEPARATOR}{sample_position_object.name}"
                        )
                    # add the sample positions back to the device
                    for sample_position_object in device_sample_position_dict[
                        device_name
                    ]:
                        self._sample_view.add_sample_positions_to_db(
                            sample_positions=[sample_position_object],
                            parent_device_name=device_name,
                        )
                    processed = True
                    logger.info(f'Sample positions in device {device_name} have been updated.')
                elif device_entry["status"] == DeviceTaskStatus.OCCUPIED.name:
                    logger.info(f'Device {device_name} is occupied, skipping and waiting for it to be unoccupied.')
                    self._device_view.pause_device(device_name)
                else:
                    logger.info(f"Device {device_name} is in status {device_entry['status']}, skipping and waiting for it to be unoccupied.")
                    self._device_view.pause_device(device_name)

        if processed:
            self.sample_positions_in_devices_to_be_updated_that_is_paused.remove(
                device_sample_position_dict
            )

    def _handle_device_sample_position_removal(self, device_sample_position_dict):
        """Handle removing sample positions from devices."""
        processed = False
        for device_name in list(device_sample_position_dict.keys()):
            sample_positions_names_in_device = (
                self._sample_view.get_sample_positions_names_by_device(device_name)
            )
            sample_positions_status = self._get_sample_positions_status(
                sample_positions_names_in_device
            )

            if all(
                status == SamplePositionStatus.EMPTY
                for status in sample_positions_status
            ):
                device_entry = self._device_view.get_device(device_name)

                if device_entry["status"] == DeviceTaskStatus.IDLE.name:
                    logger.info(f'Device {device_name} is not occupied and has no samples on it, pausing it to remove the sample positions.')
                    self._device_view.pause_device(device_name)
                    self.sample_positions_in_devices_to_be_removed_that_is_paused.append(
                        device_sample_position_dict
                    )
                    processed = True
                    logger.info(f'Device {device_name} has been paused to remove the sample positions.')
                elif device_entry["status"] == DeviceTaskStatus.OCCUPIED.name:
                    logger.info(f'Device {device_name} is occupied, skipping and waiting for it to be unoccupied.')
                    self._device_view.pause_device(device_name)
                else:
                    logger.info(f"Device {device_name} is in status {device_entry['status']}, skipping and waiting for it to be unoccupied.")

        if processed:
            self.sample_positions_in_devices_to_be_removed.remove(
                device_sample_position_dict
            )

    def _handle_device_sample_position_removal_paused(
        self, device_sample_position_dict
    ):
        """Handle removing sample positions from paused devices."""
        processed = False
        for device_name in list(device_sample_position_dict.keys()):
            sample_positions_names_in_device = (
                self._sample_view.get_sample_positions_names_by_device(device_name)
            )
            sample_positions_status = self._get_sample_positions_status(
                sample_positions_names_in_device
            )

            if all(
                status == SamplePositionStatus.EMPTY
                for status in sample_positions_status
            ):
                device_entry = self._device_view.get_device(device_name)

                if (
                    device_entry["status"] == DeviceTaskStatus.IDLE.name
                    and device_entry["pause_status"] == DevicePauseStatus.PAUSED.name
                ):
                    logger.info(f'Device {device_name} is not occupied, paused, and has no samples on it, removing the sample positions.')
                    for sample_position_object in device_sample_position_dict[
                        device_name
                    ]:
                        self._sample_view.remove_sample_position_by_prefix(
                            f"{device_name}{sample_position_object.SEPARATOR}{sample_position_object.name}"
                        )
                    processed = True
                    logger.info(f'Sample positions in device {device_name} have been removed.')
                elif device_entry["status"] == DeviceTaskStatus.OCCUPIED.name:
                    logger.info(f'Device {device_name} is occupied, skipping and waiting for it to be unoccupied.')
                    self._device_view.pause_device(device_name)
                else:
                    logger.info(f"Device {device_name} is in status {device_entry['status']}, skipping and waiting for it to be unoccupied.")
                    self._device_view.pause_device(device_name)

        if processed:
            self.sample_positions_in_devices_to_be_removed_that_is_paused.remove(
                device_sample_position_dict
            )

    def _check_sample_positions_status_and_update_or_remove_if_not_occupied(self):
        """Check the sample positions status and remove it if it is not occupied."""
        while True:
            time.sleep(10)

            # Handle standalone sample position updates
            for sample_position_object in self.sample_positions_objects_to_be_updated:
                self._handle_sample_position_update(sample_position_object)

            # Handle standalone sample position removals
            for prefix in self.sample_positions_prefixes_to_be_removed:
                self._handle_sample_position_removal(prefix)

            # Handle device sample position updates
            for (
                device_sample_position_dict
            ) in self.sample_positions_in_devices_to_be_updated:
                self._handle_device_sample_position_update(device_sample_position_dict)

            # Handle paused device sample position updates
            for (
                device_sample_position_dict
            ) in self.sample_positions_in_devices_to_be_updated_that_is_paused:
                self._handle_device_sample_position_update_paused(
                    device_sample_position_dict
                )

            # Handle device sample position removals
            for (
                device_sample_position_dict
            ) in self.sample_positions_in_devices_to_be_removed:
                self._handle_device_sample_position_removal(device_sample_position_dict)

            # Handle paused device sample position removals
            for (
                device_sample_position_dict
            ) in self.sample_positions_in_devices_to_be_removed_that_is_paused:
                self._handle_device_sample_position_removal_paused(
                    device_sample_position_dict
                )

    @contextmanager
    def pause_all_devices(self):
        """Pause all devices, so that no device can be used during the context."""
        already_paused = self._device_view.get_paused_devices()
        try:
            self._device_view.pause_all_devices()
            yield
        finally:
            self._device_view.unpause_all_devices()
            for device in already_paused:
                self._device_view.pause_device(device)

    def run(self):
        """Start to listen on the device_rpc queue and conduct the command one by one."""
        self.connection = get_rabbitmq_connection()
        with self.connection.channel() as channel:
            # Not exclusive. The queue is still auto-delete, so it goes away with this consumer
            # and a client publishing while no Device Manager is running gets an immediate
            # unroutable error rather than a request that is silently queued and then executed
            # much later against a device the requesting task no longer occupies. Exclusivity on
            # top of that buys nothing and adds a failure mode: a restarting Device Manager whose
            # previous connection has not been reaped yet gets RESOURCE_LOCKED here, which kills
            # this thread and takes the whole `alabos launch` process down with it.
            channel.queue_declare(
                queue=self._rpc_queue_name,
                auto_delete=True,
                exclusive=False,
            )
            channel.basic_consume(
                queue=self._rpc_queue_name,
                on_message_callback=self.on_message,
                auto_ack=False,
                consumer_tag=self._rpc_queue_name,
            )
            _rpc_trace_any_verbose(
                "consumer listening queue=%s",
                self._rpc_queue_name,
            )
            logger.info(
                "Device Manager RPC consumer listening on queue %s",
                self._rpc_queue_name,
            )
            channel.start_consuming()

    def _execute_command_wrapper(
        self,
        channel,
        delivery_tag,
        props,
        device,
        method,
        task_id,
        *args,
        **kwargs,
    ):
        """Execute a command on the device. Acknowledges completion on rabbitmq channel."""
        require_occupation = kwargs.pop("require_occupation", True)
        call_summary = _summarize_rpc_call(*args, **kwargs)
        correlation_id = props.correlation_id
        started_at = time.monotonic()
        _rpc_trace(
            device,
            "execute -> %s task=%s corr=%s args=(%s)",
            method,
            task_id,
            correlation_id,
            call_summary,
        )

        def callback_publish(channel, delivery_tag, props, response):
            if isinstance(response, Mock):
                raise RuntimeError(
                    f"You are trying to call a method on a Mock device. Please specify a mock value for {response}."
                )
            if props.reply_to is not None:
                channel.basic_publish(
                    exchange="",
                    routing_key=props.reply_to,
                    properties=pika.BasicProperties(
                        correlation_id=props.correlation_id,
                        content_type="application/python-dill",
                    ),
                    body=dill.dumps(response),
                )
                _rpc_trace(
                    device,
                    "reply published %s task=%s corr=%s status=%s",
                    method,
                    task_id,
                    props.correlation_id,
                    response.get("status"),
                )

            channel.basic_ack(delivery_tag=cast(int, delivery_tag))
            _rpc_trace(
                device,
                "acked %s task=%s corr=%s",
                method,
                task_id,
                props.correlation_id,
            )

        try:
            device_entry: dict[str, Any] | None = self._device_view.get_device(device)

            # check if the device is currently occupied by this task
            if self._check_status and require_occupation and (
                device_entry is None
                or device_entry["status"] != DeviceTaskStatus.OCCUPIED.name
                or device_entry["task_id"] != ObjectId(task_id)
            ):
                if device_entry is None:
                    raise PermissionError("There is no such device in the device view.")
                if device_entry["status"] != DeviceTaskStatus.OCCUPIED.name:
                    _rpc_trace(
                        device,
                        "occupation wait %s task=%s status=%s (want OCCUPIED)",
                        method,
                        task_id,
                        device_entry["status"],
                    )
                    # Wait a few seconds for the device to be OCCUPIED.
                    for _ in range(5):
                        time.sleep(1)
                        device_entry: dict[str, Any] | None = (
                            self._device_view.get_device(device)
                        )
                        if device_entry["status"] == DeviceTaskStatus.OCCUPIED.name:
                            break
                    if device_entry["status"] != DeviceTaskStatus.OCCUPIED.name:
                        raise PermissionError(
                            f"Currently the device ({device}) is NOT OCCUPIED, it is currently in status {device_entry['status']}"
                        )
                if device_entry["task_id"] != ObjectId(task_id):
                    device_task_id = str(device_entry["task_id"])
                    _rpc_trace(
                        device,
                        "occupation mismatch %s task=%s holder=%s",
                        method,
                        task_id,
                        device_task_id,
                    )
                    raise PermissionError(
                        f"Currently the task ({task_id}) "
                        f"does not occupy this device: {device}, which is currently occupied by task {device_task_id}"
                    )

            result = self._device_view.execute_command(device, method, *args, **kwargs)
            response = {"status": "success", "result": result}
        except Exception as e:
            response = {"status": "failure", "result": e}

        duration = time.monotonic() - started_at
        if response["status"] == "success":
            _rpc_trace(
                device,
                "execute <- %s task=%s corr=%s (%.2fs)",
                method,
                task_id,
                correlation_id,
                duration,
            )
        else:
            _rpc_trace(
                device,
                "execute <- %s task=%s corr=%s failed after %.2fs: %r",
                method,
                task_id,
                correlation_id,
                duration,
                response["result"],
            )

        cb = partial(callback_publish, channel, delivery_tag, props, response)
        self.connection.add_callback_threadsafe(cb)

    def on_message(
        self,
        channel: BlockingChannel,
        method: Basic.Deliver,
        props: BasicProperties,
        _body: bytes,
    ):
        """
        Function that handle the command message.

        The structure of ``_body``:

        .. code-block::

          {
              "task_id": str,
              "device": str,
              "method": str,
              "args": List,
              "kwargs": Dict,
          }
        """
        body: dict[str, Any] = dill.loads(_body)
        device_name = body["device"]
        method_name = body["method"]
        task_id = body["task_id"]
        _rpc_trace(
            device_name,
            "received %s task=%s corr=%s delivery_tag=%s queue=%s",
            method_name,
            task_id,
            props.correlation_id,
            method.delivery_tag,
            self._rpc_queue_name,
        )

        thread = Thread(
            target=self._execute_command_wrapper,
            args=(
                channel,
                method.delivery_tag,
                props,
                device_name,
                method_name,
                task_id,
                *body["args"],
            ),
            kwargs={**body["kwargs"], "require_occupation": body.get("require_occupation", True)},
        )
        self.threads.append(thread)
        thread.start()
        _rpc_trace(
            device_name,
            "dispatch thread started %s task=%s corr=%s",
            method_name,
            task_id,
            props.correlation_id,
        )


class DevicesClient:  # pylint: disable=too-many-instance-attributes
    """
    A rabbitmq-backed RPC client for sending device requests to the Device Manager (server).

    Use ``create_device_wrapper`` to create Device Wrapper instance.
    """

    def __init__(self, task_id: ObjectId, timeout: int = None):
        """
        Args:
            task_id: the task id of current task process
            timeout: the max time to wait for the server to respond, if
              the time exceed the max time, a :py:class:`TimeoutError <concurrent.futures._base.TimeoutError>`
              shall be raised.
        """
        assert task_id is not None, "task_id cannot be None!"

        self.sim_mode_flag = AlabOSConfig().is_sim_mode()
        if self.sim_mode_flag:
            self._rpc_queue_name = (
                AlabOSConfig()["general"]["name"] + "_sim" + DEFAULT_SERVER_QUEUE_SUFFIX
            )
        else:
            self._rpc_queue_name = (
                AlabOSConfig()["general"]["name"] + DEFAULT_SERVER_QUEUE_SUFFIX
            )
        # self._rpc_reply_queue_name = ( str(task_id) + DEFAULT_CLIENT_QUEUE_SUFFIX )  # TODO does this have to be
        #  taskid, or can be random? I think this dies with the resourcerequest context manager anyways?
        self._rpc_reply_queue_name = str(uuid4()) + DEFAULT_CLIENT_QUEUE_SUFFIX
        self._task_id = task_id
        # correlation_id -> (Future, device_name, method) so reply logging knows the device.
        self._waiting: dict[ObjectId, tuple[Future, str, str]] = {}

        self._conn = get_rabbitmq_connection()
        self._channel = self._conn.channel()
        self._channel.queue_declare(
            self._rpc_reply_queue_name, exclusive=True, auto_delete=True
        )
        # Device RPCs go to the default exchange, which silently discards anything it cannot
        # route. Asking for returns means an RPC sent while no Device Manager is consuming comes
        # straight back to us and fails the call, instead of the caller waiting forever for a
        # reply that nobody will ever send.
        self._channel.add_on_return_callback(self._on_returned_message)

        self._thread: Thread | None = None

        self._channel.basic_consume(
            queue=self._rpc_reply_queue_name,
            on_message_callback=self.on_message,
            auto_ack=True,
        )
        self._thread = Thread(target=self._channel.start_consuming)
        self._thread.daemon = True
        self._thread.start()

        self._timeout = timeout

    def __getitem__(self, device_name: str):
        """Get the device wrapper."""
        return self.create_device_wrapper(device_name=device_name)

    def create_device_wrapper(
        self, device_name: str
    ) -> object:  # pylint: disable=no-self-use
        """
        Create a wrapper over a device with ``device_name``.

        Args:
            device_name: the name of device to be wrapped

        Returns
        -------
            A device wrapper that will send every call to class method to remote server.
        """
        return DeviceWrapper(name=device_name, devices_client=self)

    def _fail_waiting_call(self, correlation_id: ObjectId, error: Exception):
        """Complete a pending RPC with an error instead of leaving its caller blocked."""
        waiting = self._waiting.pop(correlation_id, None)
        if waiting is None:
            return
        future, device_name, method = waiting
        _rpc_trace(
            device_name,
            "call failed to dispatch %s task=%s corr=%s: %s",
            method,
            self._task_id,
            correlation_id,
            error,
        )
        if not future.done():
            future.set_exception(error)

    def _on_returned_message(self, _channel, _method, properties, _body):
        """Handle an RPC that RabbitMQ could not deliver to the Device Manager.

        The device RPC queue only exists while the Device Manager is consuming it, so an
        unroutable message means the Device Manager is not running or has not finished starting
        up. Without this the message would simply vanish and the caller would wait forever.
        """
        try:
            correlation_id = ObjectId(properties.correlation_id)
        except Exception:
            logger.error(
                "[device-rpc] a device call was returned as undeliverable but carried no usable "
                "correlation id, so the caller cannot be notified. Is the Device Manager running?"
            )
            return
        self._fail_waiting_call(
            correlation_id,
            DeviceManagerUnavailableError(
                f"Device call could not be delivered: RabbitMQ has no queue "
                f"'{self._rpc_queue_name}'. That queue only exists while the alabos Device "
                "Manager is consuming it, so the Device Manager is either not running or has not "
                "finished starting up. Check the `alabos launch` process, and check the Devices "
                "page for devices that are still connecting -- launch waits on device "
                "connections before the Device Manager starts serving calls."
            ),
        )

    def _wait_for_rpc_result(
        self,
        future: Future,
        correlation_id: ObjectId,
        device_name: str,
        method: str,
        started_at: float,
    ) -> Any:
        if not should_trace_device(device_name):
            if self._timeout is None:
                return future.result()
            try:
                return future.result(timeout=self._timeout)
            except FuturesTimeoutError:
                self._waiting.pop(correlation_id, None)
                elapsed = time.monotonic() - started_at
                logger.error(
                    "[device-rpc] call timed out: %s.%s task=%s after %.2fs",
                    device_name,
                    method,
                    self._task_id,
                    elapsed,
                )
                raise FuturesTimeoutError(
                    f"Device RPC timed out after {self._timeout}s: "
                    f"{device_name}.{method} (task={self._task_id})"
                ) from None

        while True:
            if self._timeout is not None:
                elapsed = time.monotonic() - started_at
                remaining = self._timeout - elapsed
                if remaining <= 0:
                    self._waiting.pop(correlation_id, None)
                    raise FuturesTimeoutError(
                        f"Device RPC timed out after {self._timeout}s: "
                        f"{device_name}.{method} (task={self._task_id})"
                    )
                wait_timeout = min(DEVICE_RPC_HEARTBEAT_SECONDS, remaining)
            else:
                wait_timeout = DEVICE_RPC_HEARTBEAT_SECONDS

            try:
                return future.result(timeout=wait_timeout)
            except FuturesTimeoutError:
                elapsed = time.monotonic() - started_at
                timeout_note = (
                    f", timeout={self._timeout}s"
                    if self._timeout is not None
                    else ""
                )
                _rpc_trace(
                    device_name,
                    "call ... waiting: %s task=%s corr=%s queue=%s "
                    "(%.0fs elapsed%s; if no 'received'/'execute' lines appear, "
                    "Device Manager has not picked up this message)",
                    method,
                    self._task_id,
                    correlation_id,
                    self._rpc_queue_name,
                    elapsed,
                    timeout_note,
                )

    def call(
        self,
        device_name: str,
        method: str,
        *args,
        require_occupation: bool = True,
        **kwargs,
    ) -> Any:
        """
        Call a method inside the device with name ``device_name``. args, kwargs will be feeded into
        the method directly.

        Args:
            device_name: the name of device, which is defined by administer.
            method: the class method to call
            args: positional arguments to feed into the method function
            kwargs: keyword arguments to feed into the method function

        Returns
        -------
            the result of function
        """
        assert self._conn and self._channel

        f: Future = Future()
        correlation_id = ObjectId()
        self._waiting[correlation_id] = (f, device_name, method)
        call_summary = _summarize_rpc_call(*args, **kwargs)
        started_at = time.monotonic()
        _rpc_trace(
            device_name,
            "call -> %s task=%s corr=%s queue=%s args=(%s)",
            method,
            self._task_id,
            correlation_id,
            self._rpc_queue_name,
            call_summary,
        )

        def _publish() -> None:
            try:
                self._channel.basic_publish(
                    exchange="",
                    routing_key=self._rpc_queue_name,
                    body=dill.dumps(
                        {
                            "device": device_name,
                            "method": method,
                            "args": args,
                            "kwargs": kwargs,
                            "task_id": str(self._task_id),
                            "require_occupation": require_occupation,
                        }
                    ),
                    properties=BasicProperties(
                        reply_to=self._rpc_reply_queue_name,
                        content_type="application/python-dill",
                        correlation_id=str(correlation_id),
                    ),
                    mandatory=True,
                )
            except Exception as e:
                # Runs on the pika I/O thread, where raising would take down the reply consumer.
                # Hand the error to the waiting caller instead.
                self._fail_waiting_call(correlation_id, e)
                return
            _rpc_trace(
                device_name,
                "published %s task=%s corr=%s queue=%s",
                method,
                self._task_id,
                correlation_id,
                self._rpc_queue_name,
            )

        self._conn.add_callback_threadsafe(_publish)
        try:
            result = self._wait_for_rpc_result(
                f,
                correlation_id,
                device_name,
                method,
                started_at,
            )
        except FuturesTimeoutError:
            elapsed = time.monotonic() - started_at
            logger.error(
                "[device-rpc] call timed out: %s.%s task=%s after %.2fs",
                device_name,
                method,
                self._task_id,
                elapsed,
            )
            raise

        duration = time.monotonic() - started_at
        _rpc_trace(
            device_name,
            "call <- %s task=%s corr=%s (%.2fs)",
            method,
            self._task_id,
            correlation_id,
            duration,
        )
        return result

    def on_message(
        self,
        channel: BlockingChannel,
        method_frame: Basic.Deliver,  # pylint: disable=unused-argument
        properties: BasicProperties,
        _body: bytes,
    ):
        """Callback function to handle a returned message from Device Manager."""
        correlation_id = ObjectId(properties.correlation_id)
        waiting = self._waiting.pop(correlation_id, None)
        if waiting is None:
            logger.warning(
                "[device-rpc] reply for unknown corr=%s (already timed out or cancelled?)",
                correlation_id,
            )
            return
        f, device_name, method_name = waiting

        try:
            body = dill.loads(_body)
            _rpc_trace(
                device_name,
                "reply received %s corr=%s status=%s",
                method_name,
                correlation_id,
                body.get("status"),
            )

            if body["status"] == "success":
                f.set_result(body["result"])
            else:
                f.set_exception(body["result"])
        except Exception as e:
            f.set_exception(e)
