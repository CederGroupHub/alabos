"""Wrapper over the ``devices`` collection."""

import logging

logger = logging.getLogger(__name__)
import time
from collections.abc import Collection
from datetime import datetime
from enum import Enum, auto, unique
from typing import Any, TypeVar, cast

import pymongo  # type: ignore
from bson import ObjectId  # type: ignore
from threading import Event, Lock, Thread

from alab_management.sample_view import SamplePosition, SampleView
from alab_management.utils.data_objects import get_collection, get_lock

from .device import BaseDevice, get_all_devices, remove_device

_DeviceType = TypeVar("_DeviceType", bound=BaseDevice)  # pylint: disable=invalid-name


#: How long to wait for a single device to finish connecting before giving up on it *for now* and
#: moving on to the next one. A device that overruns this is not abandoned: its connection keeps
#: running in the background and the device joins the lab the moment it succeeds. This exists so
#: that one unreachable -- or interactively blocked -- device can never stop the rest of the lab
#: from launching.
DEFAULT_DEVICE_CONNECT_TIMEOUT = 60.0

#: Upper bound on the total time the connect phase may spend waiting on slow devices. Without it,
#: N slow devices would each cost the full per-device timeout and launch would still be held up for
#: N * timeout. Once this budget is spent, remaining devices get only a token wait; any that do not
#: make it are picked up by the watcher and join a few seconds later.
DEFAULT_TOTAL_CONNECT_BUDGET = 180.0

#: The shortest we will ever wait on a device, so that a spent budget cannot skip devices that
#: connect essentially instantly.
MIN_DEVICE_CONNECT_WAIT = 2.0

#: How often the background watcher re-checks devices that are still connecting.
CONNECTION_WATCH_INTERVAL = 5.0


class DeviceConnectionError(Exception):
    """Generic error signifying that connection to a device has failed."""


@unique
class DeviceTaskStatus(Enum):
    """The Task status of devices. Used by TaskManager to decide whether a Device is available for to execute a Task."""

    UNKNOWN = auto()
    IDLE = auto()
    OCCUPIED = auto()
    ERROR = auto()


@unique
class DevicePauseStatus(Enum):
    """Pause status of the Device. This is used to pause the device outside of the typical Task queue (like by an
    operator for maintenance or refilling consumables).
    """

    RELEASED = auto()
    REQUESTED = auto()
    PAUSED = auto()


class DeviceView:
    """
    Device view provides API to get/set the status
    of a device as well as request ownership of one device.
    """

    def __init__(self, connect_to_devices: bool = False):
        """Class with methods to interact with devices (status + method execution).

        Args:
            connect_to_devices (Optional[bool]): If true, make a connection to all devices
              (serial, ip, etc.). If False, can still check Device status, but cannot execute
              methods on devices. Defaults to False.
        """
        self._device_collection = get_collection("devices")
        self._device_collection.create_index([("name", pymongo.HASHED)])
        self._device_list = get_all_devices()
        self._lock = get_lock(self._device_collection.name)
        self.__connected_to_devices = False
        self._connected_device_names: set[str] = set()
        self._sample_view = SampleView()

        # Bookkeeping for devices whose connection overran the timeout and is still running in
        # the background. Guarded by _connection_lock because the watcher thread reads them.
        self._connection_lock = Lock()
        self._pending_connections: dict[str, Thread] = {}
        self._connection_results: dict[str, dict[str, Any]] = {}
        self._connection_started_at: dict[str, float] = {}
        self._paused_for_connection: set[str] = set()
        self._connection_watcher: Thread | None = None
        self._connection_watcher_stop = Event()
        self._user_input_view = None

        if connect_to_devices:
            self.__connect_all_devices()

    @staticmethod
    def _device_connect_timeout() -> float:
        """Per-device connection timeout, overridable as ``general.device_connect_timeout``."""
        from alab_management.config import AlabOSConfig

        try:
            return float(
                AlabOSConfig()["general"].get(
                    "device_connect_timeout", DEFAULT_DEVICE_CONNECT_TIMEOUT
                )
            )
        except Exception:
            return DEFAULT_DEVICE_CONNECT_TIMEOUT

    def __connect_all_devices(self):
        """Connect to every device without letting any single device hold up the launch.

        Each device is connected in its own thread and waited on for at most
        ``device_connect_timeout`` seconds. Three things can happen:

        * it connects, and is marked as connected;
        * it raises, and is disabled and paused so the rest of the lab still runs;
        * it neither returns nor raises within the timeout -- typically a driver blocking on a
          maintenance prompt, or a hardware connection with no timeout of its own.

        The third case is why this is threaded at all. Such a device is left connecting in the
        background and marked ``connecting`` on the dashboard, and the rest of the devices are
        connected as normal. This matters because the caller of this method is
        ``DeviceManager.__init__``, which must return for ``DeviceManager.run()`` to declare and
        consume the device RPC queue. Blocking here means no device RPC for the *entire lab*, and
        because RPC calls are published to the default exchange they are silently dropped rather
        than queued, so every device call in the lab hangs forever with no error.
        """
        timeout = self._device_connect_timeout()
        deadline = time.monotonic() + DEFAULT_TOTAL_CONNECT_BUDGET
        for device_name, device in self._device_list.items():
            remaining_budget = deadline - time.monotonic()
            wait = min(timeout, max(remaining_budget, MIN_DEVICE_CONNECT_WAIT))
            self._connect_one_device(device_name, device, wait)
        self.__connected_to_devices = True
        self._start_connection_watcher()

    def _connect_one_device(self, device_name: str, device: BaseDevice, timeout: float):
        """Connect a single device, giving up the wait (but not the attempt) after ``timeout``."""
        started_at = time.monotonic()
        result: dict[str, Any] = {}

        def _connect():
            try:
                device._connect_wrapper()
            except Exception as e:  # recorded rather than raised: this runs in its own thread
                result["error"] = e
            else:
                result["connected"] = True

        thread = Thread(
            target=_connect, name=f"connect-{device_name}", daemon=True
        )
        thread.start()
        thread.join(timeout)

        if not thread.is_alive():
            self._finish_device_connection(device_name, result)
            return

        # Deliberately not killed: the connection may well succeed later (e.g. once an operator
        # answers the prompt it is waiting on), and interrupting a half-open hardware connection
        # is worse than leaving it to finish.
        with self._connection_lock:
            self._pending_connections[device_name] = thread
            self._connection_results[device_name] = result
            self._connection_started_at[device_name] = started_at
        logger.warning(
            "Still connecting to %s after %.0fs. Continuing without it so the rest of the lab can "
            "launch; it will join automatically when the connection completes.",
            device_name,
            timeout,
        )
        self._mark_device_connecting(device_name, timeout)

    def _finish_device_connection(self, device_name: str, result: dict[str, Any]):
        """Apply the outcome of a device's connection attempt."""
        error = result.get("error")
        if error is not None:
            logger.error(
                "Could not connect to %s: %r. Disabling and pausing it so the rest of the lab can still launch.",
                device_name,
                error,
            )
            self._mark_device_connection_failed(device_name, error)
            return
        with self._connection_lock:
            self._connected_device_names.add(device_name)
        self._mark_device_connected(device_name)
        logger.info("Connecting to %s... Done", device_name)

    def _start_connection_watcher(self):
        """Watch devices that are still connecting so they can join the lab without a relaunch."""
        with self._connection_lock:
            if not self._pending_connections:
                return
        self._connection_watcher_stop.clear()
        self._connection_watcher = Thread(
            target=self._watch_pending_connections,
            name="device-connection-watcher",
            daemon=True,
        )
        self._connection_watcher.start()

    def _watch_pending_connections(self):
        while not self._connection_watcher_stop.is_set():
            with self._connection_lock:
                pending = list(self._pending_connections.items())
            if not pending:
                return
            for device_name, thread in pending:
                with self._connection_lock:
                    started_at = self._connection_started_at.get(
                        device_name, time.monotonic()
                    )
                if thread.is_alive():
                    # Refresh the dashboard message: what the device is blocked on can change
                    # (a driver may raise a new prompt after the previous one is answered).
                    self._mark_device_connecting(
                        device_name, time.monotonic() - started_at
                    )
                    continue
                with self._connection_lock:
                    self._pending_connections.pop(device_name, None)
                    result = self._connection_results.pop(device_name, {})
                    self._connection_started_at.pop(device_name, None)
                self._finish_device_connection(device_name, result)
            self._connection_watcher_stop.wait(CONNECTION_WATCH_INTERVAL)

    def _pending_user_input_for_device(self, device_name: str) -> dict[str, Any] | None:
        """The unanswered dashboard request this device raised, if it is waiting on one."""
        try:
            if self._user_input_view is None:
                from alab_management.user_input import UserInputView

                self._user_input_view = UserInputView()
            return self._user_input_view.get_pending_request_by_context(
                {"device": device_name}
            )
        except Exception:
            return None

    def _update_connection_attributes(self, device_name: str, **values: Any):
        """Set connection bookkeeping attributes individually.

        Uses dotted ``$set`` paths rather than ``set_attribute`` so that rewriting connection
        state never clobbers attribute values a running driver wrote in the meantime.
        """
        update: dict[str, Any] = {
            f"attributes.{key}": value for key, value in values.items()
        }
        update["last_updated"] = datetime.now()
        self._device_collection.update_one({"name": device_name}, {"$set": update})

    def _mark_device_connecting(self, device_name: str, waited_seconds: float):
        """Flag a device as still connecting, recording what it is waiting on.

        The device is paused (so no task can acquire something that is not ready) but is *not*
        marked disabled, because it is expected to come good on its own.
        """
        try:
            pending_request = self._pending_user_input_for_device(device_name)
            if pending_request is not None:
                message = (
                    "NOT CONNECTED: alabos is still connecting to this device "
                    f"({waited_seconds:.0f}s so far). It is waiting for an operator to answer a "
                    'request. Go to "User Input Requests" and respond to: '
                    f'"{pending_request.get("prompt", "")}". The device will join the lab '
                    "automatically once you respond -- no need to restart the lab."
                )
            else:
                message = (
                    "NOT CONNECTED: alabos is still connecting to this device "
                    f"({waited_seconds:.0f}s so far). The rest of the lab has launched without "
                    "it. It will join automatically once the connection completes -- no need to "
                    'restart the lab. If it stays like this, check "User Input Requests" and '
                    "that the hardware is powered on and reachable."
                )

            was_connecting = False
            try:
                attributes = self.get_device(device_name).get("attributes") or {}
                was_connecting = attributes.get("connection_status") == "connecting"
            except Exception:
                pass

            self._update_connection_attributes(
                device_name,
                connection_status="connecting",
                connection_error=None,
                connection_waiting_seconds=round(waited_seconds),
                connection_blocked_on_user_input=pending_request is not None,
                connection_user_input_prompt=(
                    pending_request.get("prompt") if pending_request else None
                ),
            )
            if not was_connecting:
                # Only pause on the first pass, so repeated refreshes cannot fight an operator
                # who deliberately released the device.
                self.pause_device(device_name)
                self._paused_for_connection.add(device_name)
            self.set_message(device_name, message)
        except Exception as exc:  # best-effort bookkeeping; never block launch
            logger.error(f"Failed to flag {device_name} as connecting: {exc!r}")

    def _mark_device_connected(self, device_name: str):
        """Record that a device is connected and usable, clearing any connecting/failed state."""
        try:
            self._update_connection_attributes(
                device_name,
                connection_status="connected",
                connection_error=None,
                connection_waiting_seconds=None,
                connection_blocked_on_user_input=False,
                connection_user_input_prompt=None,
            )
        except Exception as exc:
            logger.error(f"Failed to record {device_name} as connected: {exc!r}")
        # Release the pause this class applied while the device was connecting. An operator pause
        # is left alone: we only undo what we did ourselves.
        if device_name in self._paused_for_connection:
            self._paused_for_connection.discard(device_name)
            try:
                self.unpause_device(device_name)
                self.set_message(device_name, "")
            except Exception as exc:
                logger.error(f"Failed to unpause {device_name} after connecting: {exc!r}")
        # If this device was previously auto-disabled due to a connection failure and is
        # now reachable again, clear that flag so it becomes usable.
        self._clear_connection_failed_flag(device_name)

    def __disconnect_all_devices(self):
        self._connection_watcher_stop.set()
        # Only disconnect devices that actually connected; devices that failed to connect
        # never opened a connection and may not be safe to disconnect.
        for device_name in list(self._connected_device_names):
            device = self._device_list.get(device_name)
            if device is None:
                continue
            logger.info(f"Disconnecting from {device_name}...")
            try:
                device._disconnect_wrapper()
            except Exception as e:
                logger.error(f"Could not disconnect from {device_name}: {e!r}")
                continue
            logger.info("Disconnected from %s", device_name)
        self._connected_device_names.clear()
        self.__connected_to_devices = False

    def _mark_device_connection_failed(self, device_name: str, error: Exception):
        """Flag a device as disabled because alabos could not connect to it.

        The device stays registered (so it still appears on the dashboard) but is paused so
        no task can acquire it, and its attributes record why it is disabled so the UI can
        explain it to operators.
        """
        message = (
            "NOT CONNECTED: alabos could not establish a connection to this device "
            f"({type(error).__name__}: {error}). It is disabled and paused, and cannot be used "
            "until the connection is restored and the lab is relaunched."
        )
        try:
            self.pause_device(device_name)
            self._paused_for_connection.discard(device_name)
            self.set_attribute(device_name, "disabled", True)
            self.set_attribute(device_name, "disabled_reason", "connection_failed")
            self._update_connection_attributes(
                device_name,
                connection_status="failed",
                connection_error=f"{type(error).__name__}: {error}",
                connection_waiting_seconds=None,
                connection_blocked_on_user_input=False,
                connection_user_input_prompt=None,
            )
            self.set_message(device_name, message)
        except Exception as exc:  # best-effort bookkeeping; never block launch
            logger.error(f'Failed to flag {device_name} as disabled: {exc!r}')

    def _clear_connection_failed_flag(self, device_name: str):
        """Clear a previous connection-failure disable once a device connects again.

        Manual disables (``disabled_reason`` other than ``"connection_failed"``) are left
        untouched so intentionally disabled devices stay disabled.
        """
        try:
            device_entry = self.get_device(device_name)
        except Exception:
            return
        attributes = device_entry.get("attributes", {}) or {}
        if (
            attributes.get("disabled")
            and attributes.get("disabled_reason") == "connection_failed"
        ):
            self.set_attribute(device_name, "disabled", False)
            self.set_attribute(device_name, "disabled_reason", None)
            self.unpause_device(device_name)
            self.set_message(device_name, "")

    def sync_device_status(self):
        """
        Sync the device status (usually when the system is set up).

        Some devices may still be running, so it is not usable now. We will set the
        status to ``OCCUPIED``
        """
        for device in self._device_list.values():
            status = (
                DeviceTaskStatus.OCCUPIED
                if device.is_running()
                else DeviceTaskStatus.IDLE
            )
            self._update_status(
                device=device.name,
                target_status=status,
                required_status=None,
                task_id=None,
            )

    def add_devices_to_db(self, devices: dict[str, BaseDevice] | None = None):
        """
        Insert device definitions to db, which includes devices' name, descriptions, parameters,
        type (class name).

        When one device's name has already appeared in the database, a ``NameError`` will be raised.
        Device name is a unique identifier for a device
        """
        for device in (
            devices.values() if devices is not None else self._device_list.values()
        ):
            if self._device_collection.find_one({"name": device.name}) is not None:
                raise NameError(
                    f"Duplicated device name {device.name}, did you cleanup the database?"
                )
            self._device_collection.insert_one(
                {
                    "name": device.name,
                    "description": device.description,
                    "type": device.__class__.__name__,
                    "sample_positions": [
                        f"{device.name}{SamplePosition.SEPARATOR}{sample_pos.name}"
                        for sample_pos in device.sample_positions
                    ],
                    "status": DeviceTaskStatus.IDLE.name,
                    "pause_status": DevicePauseStatus.RELEASED.name,
                    "task_id": None,
                    "created_at": datetime.now(),
                    "message": "",
                    "last_updated": datetime.now(),
                    "attributes": {},
                    "dashboard_attributes": list(device.dashboard_attributes),
                }
            )

    def sync_device_definitions(self, devices: dict[str, BaseDevice] | None = None):
        """Refresh the definition-only fields of devices that are already in the database.

        ``add_devices_to_db`` only ever inserts, so a device that already exists never picks up
        changes made to its class. This copies across the fields that describe the device rather
        than its state -- its description and which attributes the dashboard may show -- so editing
        them in code and re-running ``alabos setup`` is enough. Nothing here touches status,
        occupancy or attribute values.
        """
        for device in (
            devices.values() if devices is not None else self._device_list.values()
        ):
            self._device_collection.update_one(
                {"name": device.name},
                {
                    "$set": {
                        "description": device.description,
                        "dashboard_attributes": list(device.dashboard_attributes),
                    }
                },
            )

    def get_all(self) -> list[dict[str, Any]]:
        """Get all the devices in the database, used for dashboard."""
        return cast("list[dict[str, Any]]", self._device_collection.find())

    def _clean_up_device_collection(self):
        """Clean up the device collection."""
        self._device_collection.drop()

    def request_devices(
        self,
        task_id: ObjectId,
        device_names_str: Collection[str] | None = None,
        device_types_str: (
            Collection[str] | None
        ) = None,  # pylint: disable=unsubscriptable-object
    ) -> dict[str, dict[str, str | bool]] | None:
        """
        Request a list of device, this function will return the name of devices if all the requested device is ready.

        .. note::
            There should be no duplicated devices in the ``device_type``, or a ``ValueError`` shall be raised

        Args:
            task_id (ObjectId): the id of task that requests these devices
            device_names_str (Optional[Collection[str]]): the requested
              device names. If None, no device name is requested
            device_types_str (Optional[Collection[str]]): the requested
              device types. If None, no device type is requested

        Returns
        -------
            {"device_type_name": {"name": device_name, "need_release": need_release (bool)}} or None
        """
        if device_names_str is None:
            device_names_str = []

        if device_types_str is None:
            device_types_str = []

        if len(device_types_str) != len(set(device_types_str)):
            raise ValueError(
                "Currently we do not allow duplicated device types in one request."
            )

        idle_devices: dict[str, dict[str, str | bool]] = {}
        with self._lock():  # pylint: disable=not-callable
            for device_name in device_names_str:
                result = self.get_available_devices(
                    device_str=device_name, type_or_name="name", task_id=task_id
                )
                if not result:
                    return None  # cannot meet all requirement, return None
                idle_devices[device_name] = result[0]
            for device in device_types_str:
                result = self.get_available_devices(
                    device_str=device, type_or_name="type", task_id=task_id
                )
                if not result:
                    return None
                same_task_devices = list(
                    filter(lambda device_: not device_["need_release"], result)
                )
                if len(same_task_devices) > 0:
                    # just pick the first device
                    idle_devices[device] = same_task_devices[0]
                else:
                    # if no device is held by the same task, pick the device with least samples
                    minimum_number_of_samples = 999999999
                    for device_ in result:
                        samples_on_device_ = self._sample_view.get_samples_on_device(
                            device_["name"]
                        )
                        number_of_samples_in_device_ = sum(
                            len(samples) for samples in samples_on_device_.values()
                        )
                        if number_of_samples_in_device_ < minimum_number_of_samples:
                            minimum_number_of_samples = number_of_samples_in_device_
                            idle_devices[device] = device_
            return idle_devices

    def get_samples_on_device(self, device_name: str) -> dict[str, list[ObjectId]]:
        """
        Get all the samples on a device.

        This function will directly call the ``SampleView.get_samples_on_device`` method for
        backward compatibility.

        .. note::

            (in version 1.0.1) This function has been moved to ``SampleView`` class.
        """
        return self._sample_view.get_samples_on_device(device_name)

    def get_available_devices(
        self, device_str: str, type_or_name: str, task_id: ObjectId | None = None
    ) -> list[dict[str, str | bool]]:
        """
        Given device type, it will return all the device with this type.

        If only_idle set to True, only the idle devices will be returned (or ones have the same task id)

        Args:
            device_str (str): the type of device
            type_or_name: "type" or "name" to specify whether searching for a type of device by
              Type(BaseDevice), or for a specific device by name
            task_id: the id of task that requests this device

        Returns
        -------
            [{"name": device_name, "need_release": bool}]
            The entry need_release indicates whether a device needs to be released
            when __exit__ method is called in the ``DevicesLock``.
        """
        if type_or_name == "type":
            request_dict = {
                "type": device_str,
            }
        elif type_or_name == "name":
            request_dict = {"name": device_str}
        else:
            raise ValueError(f"Unknown type_or_name: {type_or_name}")

        if self._device_collection.find_one(request_dict) is None:
            raise ValueError(f"No such device of {type_or_name} {device_str}")

        request_dict.update(
            {
                "$or": [
                    {  # type: ignore
                        "$and": [
                            {"status": DeviceTaskStatus.IDLE.name},
                            {"pause_status": DevicePauseStatus.RELEASED.name},
                        ]
                    },
                    {
                        "task_id": task_id,
                    },
                ]
            }
        )

        return [
            {
                "name": device_entry["name"],
                # if device already held by this task, don't release with
                # this request. Will be released by the older request.
                "need_release": device_entry["task_id"] != task_id,
            }
            for device_entry in self._device_collection.find(request_dict)
        ]

    def get_device(self, device_name: str) -> dict[str, Any]:
        """Get device by device name, if not found, raises ``ValueError``."""
        device_entry = self._device_collection.find_one({"name": device_name})
        if device_entry is None:
            raise ValueError(f"Cannot find device with name: {device_name}")
        return device_entry

    def get_status(self, device_name: str) -> DeviceTaskStatus:
        """Get device status by device name, if not found, raise ``ValueError``."""
        device_entry = self.get_device(device_name=device_name)
        return DeviceTaskStatus[device_entry["status"]]

    def occupy_device(self, device: BaseDevice | str, task_id: ObjectId):
        """Occupy a device with given task id."""
        self._update_status(
            device=device,
            required_status=DeviceTaskStatus.IDLE,
            target_status=DeviceTaskStatus.OCCUPIED,
            task_id=task_id,
        )
        device_name = device.name if isinstance(device, BaseDevice) else device
        # Wait until the device status has been updated to OCCUPIED
        while (
            self.get_status(device_name=device_name).name
            != DeviceTaskStatus.OCCUPIED.name
        ):
            time.sleep(0.5)

    def get_devices_by_task(self, task_id: ObjectId | None) -> list[BaseDevice]:
        """Get devices given a task id (regardless of its status!)."""
        return [
            self._device_list[device["name"]]
            for device in self._device_collection.find({"task_id": task_id})
        ]

    def release_device(self, device_name: str):
        """
        Release a device.

        device: name of device to be released
        """
        device_entry = self.get_device(device_name=device_name)

        update_dict = {
            "task_id": None,
            "last_updated": datetime.now(),
            "status": DeviceTaskStatus.IDLE.name,
        }

        if (
            DevicePauseStatus[device_entry["pause_status"]]
            == DevicePauseStatus.REQUESTED
        ):
            update_dict.update(
                {
                    "pause_status": DevicePauseStatus.PAUSED.name,
                }
            )

        self._device_collection.update_one(
            {"name": device_name},
            {"$set": update_dict},
        )
        # wait until the device status has been updated to IDLE
        while self.get_status(device_name=device_name).name != "IDLE":
            time.sleep(0.5)

    def _update_status(
        self,
        device: BaseDevice | str,
        required_status: DeviceTaskStatus | list[DeviceTaskStatus] | None,
        target_status: DeviceTaskStatus,
        task_id: ObjectId | None,
    ):
        """
        A method that check and update the status of a device.

        If ``task_id`` is the same as the task id in queried sample,
        we will just skip the status check specified by ``required_status``
        """
        device_name = device.name if isinstance(device, BaseDevice) else device

        device_entry = self._device_collection.find_one({"name": device_name})

        if device_entry is None:
            raise ValueError(
                f"Cannot find device ({device_name}). Did you run `setup` command?"
            )

        required_status = (
            [required_status]
            if isinstance(required_status, DeviceTaskStatus)
            else required_status
        )

        # if task_id has the same value, we will not check the current status
        if device_entry["task_id"] == task_id:
            required_status = None

        if (
            required_status is not None
            and DeviceTaskStatus[device_entry["status"]] not in required_status
        ):
            raise ValueError(
                f"Device's current status ({device_entry['status']}) is "
                f"not in allowed set of statuses {[status.name for status in required_status]}. "
                f"Cannot change status to {target_status.name}"
            )
        self._device_collection.update_one(
            {"name": device_name},
            {
                "$set": {
                    "status": target_status.name,
                    "task_id": task_id,
                    "last_updated": datetime.now(),
                }
            },
        )

    def query_property(self, device_name: str, prop: str):
        """
        Query the property value of a device (with ``device_name``) with ``prop``.

        If there is no such device with name ``device_name``, a ``ValueError`` shall be raised.
        If there is no such property with name ``prop``, a ``AttributeError`` shall be raised.
        """
        if device_name not in self._device_list:
            raise ValueError(f"Cannot find device with name: {device_name}")
        device: BaseDevice = self._device_list[device_name]

        if not hasattr(device, prop):
            raise AttributeError(
                f"Cannot find method with name: {prop} on {device_name}"
            )

        return getattr(device, prop)

    def execute_command(self, device_name: str, method: str, *args, **kwargs):
        """Call a callable function (``method``) with ``*args`` and ``**kwargs`` on ``device_name``."""
        if not self.__connected_to_devices:
            raise Exception(
                "DeviceView cannot execute device commands without first connecting to the devices!"
            )
        # Launch no longer waits for every device, so a command can arrive for a device that has
        # not finished connecting. Fail with something an operator can act on rather than letting
        # the call reach a half-initialised driver.
        with self._connection_lock:
            connected = device_name in self._connected_device_names
            still_connecting = device_name in self._pending_connections
        if not connected:
            raise DeviceConnectionError(
                self._not_connected_reason(device_name, still_connecting)
            )
        device_method = self.query_property(device_name=device_name, prop=method)
        return device_method(*args, **kwargs)

    def _not_connected_reason(self, device_name: str, still_connecting: bool) -> str:
        """An operator-facing explanation of why a device cannot take commands."""
        if still_connecting:
            pending_request = self._pending_user_input_for_device(device_name)
            if pending_request is not None:
                return (
                    f"Device {device_name} has not finished connecting: it is waiting for an "
                    'operator to answer a request. Go to "User Input Requests" on the dashboard '
                    f'and respond to: "{pending_request.get("prompt", "")}". The device will '
                    "become usable as soon as you respond."
                )
            return (
                f"Device {device_name} has not finished connecting yet. The lab launched without "
                "it and it will become usable once the connection completes. Check "
                '"User Input Requests" and that the hardware is powered on and reachable.'
            )
        return (
            f"Device {device_name} is not connected. alabos could not establish a connection to "
            "it at launch, so it is disabled. Check the Devices page for the connection error."
        )

    def set_message(self, device_name: str, message: str):
        """Sets the device message. Message is used to communicate device state with the user dashboard.

        Args:
            device_name (str): name of the device to set the message for
            message (str): message to be set
        """
        self.get_device(device_name=device_name)
        self._device_collection.update_one(
            {"name": device_name},
            {"$set": {"message": message, "last_updated": datetime.now()}},
        )

    def get_message(self, device_name: str) -> str:
        """Gets the current device message. Message is used to communicate device state with the user dashboard.

        Args:
            device_name (str): name of the device to set the message for
        """
        return self.get_device(device_name=device_name)["message"]

    def get_all_attributes(self, device_name: str) -> dict[str, Any]:
        """Returns the device attributes.

        Args:
            device_name (str): name of the device to get the attributes for

        Returns
        -------
            dict: device attributes
        """
        device = self.get_device(device_name=device_name)
        return device["attributes"]

    def get_attribute(self, device_name: str, attribute: str) -> Any:
        """Gets a device attribute. Attributes are used to store device-specific values in the database.

        Args:
            device_name (str): name of the device to get the attribute for
            attribute (str): attribute to be retrieved

        Returns
        -------
            Any: attribute value
        """
        device = self.get_device(device_name=device_name)
        if attribute not in device["attributes"]:
            raise AttributeError(
                f"Device {device_name} does not have attribute {attribute}"
            )
        return device["attributes"][attribute]

    def set_all_attributes(self, device_name: str, attributes: dict):
        """Sets the device attributes.

        Args:
            device_name (str): name of the device to set the attributes for
            attributes (dict): attributes to be set
        """
        self.get_device(device_name=device_name)
        self._device_collection.update_one(
            {"name": device_name},
            {
                "$set": {
                    "attributes": attributes,
                    "last_updated": datetime.now(),
                }
            },
        )

    def set_attribute(self, device_name: str, attribute: str, value: Any):
        """Sets a device attribute. Attributes are used to store device-specific values in the database.

        Args:
            device_name (str): name of the device to set the attribute for
            attribute (str): attribute to be set
            value (Any): attribute value
        """
        attributes = self.get_all_attributes(device_name=device_name)
        attributes[attribute] = value
        self._device_collection.update_one(
            {"name": device_name},
            {
                "$set": {
                    "attributes": attributes,
                    "last_updated": datetime.now(),
                }
            },
        )

    def pause_device(self, device_name: str):
        """Request pause for a specific device."""
        # with self._lock():
        device = self.get_device(device_name=device_name)
        new_pause_status = (
            DevicePauseStatus.PAUSED.name
            if device["status"] == DeviceTaskStatus.IDLE.name
            else DevicePauseStatus.REQUESTED.name
        )

        self._device_collection.update_one(
            {"name": device_name},
            {
                "$set": {
                    "pause_status": new_pause_status,
                    "last_updated": datetime.now(),
                }
            },
        )

    def unpause_device(self, device_name: str):
        """Unpause a device."""
        # with self._lock():
        device = self.get_device(device_name=device_name)
        update_dict = {
            "pause_status": DevicePauseStatus.RELEASED.name,
            "last_updated": datetime.now(),
        }

        # Unless the device is currently paused, we will leave its task status unchanged.
        if DevicePauseStatus[device["pause_status"]] == DevicePauseStatus.PAUSED:
            update_dict.update(
                {
                    "status": DeviceTaskStatus.IDLE.name,
                }
            )

        self._device_collection.update_one(
            {"name": device_name},
            {"$set": update_dict},
        )

    def get_paused_devices(
        self, paused_status=(DevicePauseStatus.PAUSED, DevicePauseStatus.REQUESTED)
    ) -> list[str]:
        """Get a list of paused or waiting for paused devices."""
        paused_devices = self._device_collection.find(
            {"pause_status": {"$in": [status.name for status in paused_status]}}
        )
        return [device["name"] for device in paused_devices]

    def pause_all_devices(self):
        """Pause all devices."""
        for device in self._device_list.values():
            self.pause_device(device.name)

    def unpause_all_devices(self):
        """Unpause all devices."""
        for device in self._device_list.values():
            self.unpause_device(device.name)

    def __exit__(self, exc_type, exc_value, traceback):
        """Disconnect from all devices when exiting the context manager."""
        if self.__connected_to_devices:
            self.__disconnect_all_devices()

    def close(self):
        """Disconnect from all devices when closing the DeviceView."""
        if self.__connected_to_devices:
            self.__disconnect_all_devices()

    def __del__(self):
        """Ensure that we disconnect from all devices when the object is deleted."""
        if self.__connected_to_devices:
            self.__disconnect_all_devices()

    def remove_device(self, device_name: str):
        """Remove a device from the device view and the registry."""
        # disconnect the device
        logger.info(f'Disconnecting from {device_name}...')
        with self._lock():  # pylint: disable=not-callable
            device = self._device_list[device_name]
            device._disconnect_wrapper()
            self._device_list.pop(device_name, None)
            remove_device(device_name)
            self._device_collection.delete_one({"name": device_name})
            logger.info(f'Device {device_name} has been removed from the device view and the registry.')

    def get_all_devices_from_db(self) -> dict[str, dict[str, Any]]:
        """
        Get all devices from the database directly.

        Returns a dictionary mapping device names to their database entries.
        """
        devices = {}
        for device_doc in self._device_collection.find():
            devices[device_doc["name"]] = device_doc
        return devices

    def get_device_by_name_from_db(self, device_name: str) -> dict[str, Any] | None:
        """
        Get a specific device from the database by name.

        Args:
            device_name: The name of the device to find

        Returns
        -------
            The device document from the database, or None if not found
        """
        return self._device_collection.find_one({"name": device_name})

    def device_exists_in_db(self, device_name: str) -> bool:
        """
        Check if a device exists in the database.

        Args:
            device_name: The name of the device to check

        Returns
        -------
            True if the device exists in the database, False otherwise
        """
        return self._device_collection.count_documents({"name": device_name}) > 0
