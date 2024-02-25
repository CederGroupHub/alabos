"""
This module is adapted from https://github.com/Mause/rpc.

The task process can only get access to a wrapper over the real device object. The wrapper will
redirect all the method calls to the real device object via RabbitMQ. The real device object is in
DeviceManager class, which will handle all the request to run certain methods on the real device.
"""

from concurrent.futures import Future
from enum import Enum, auto
from functools import partial
from threading import Thread
from typing import Any, Callable, Dict, NoReturn, Optional, cast
from uuid import uuid4

import dill
import pika
from bson import ObjectId
from pika import BasicProperties
from pika.adapters.blocking_connection import BlockingChannel
from pika.spec import Basic

from .config import AlabOSConfig
from .device_view.device_view import DeviceTaskStatus, DeviceView
from .utils.data_objects import get_rabbitmq_connection
from .utils.module_ops import load_definition

DEFAULT_SERVER_QUEUE_SUFFIX = ".device_rpc"
DEFAULT_CLIENT_QUEUE_SUFFIX = DEFAULT_SERVER_QUEUE_SUFFIX + ".reply_to"


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
        self._check_status = _check_status
        self.threads = []

    def run(self):
        """Start to listen on the device_rpc queue and conduct the command one by one."""
        self.connection = get_rabbitmq_connection()
        with self.connection.channel() as channel:
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

        def callback_publish(channel, delivery_tag, props, response):
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

            channel.basic_ack(delivery_tag=cast(int, delivery_tag))

        try:
            device_entry: Optional[Dict[str, Any]] = self._device_view.get_device(
                device
            )

            # check if the device is currently occupied by this task
            if self._check_status and (
                device_entry is None
                or device_entry["status"] != DeviceTaskStatus.OCCUPIED.name
                or device_entry["task_id"] != ObjectId(task_id)
            ):
                raise PermissionError(
                    f"Currently the task ({task_id}) "
                    f"does not occupy this device: {device}, which is currently occupied by task {task_id}"
                )

            result = self._device_view.execute_command(device, method, *args, **kwargs)
            response = {"status": "success", "result": result}
        except Exception as e:
            response = {"status": "failure", "result": e}

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
        body: Dict[str, Any] = dill.loads(_body)

        thread = Thread(
            target=self._execute_command_wrapper,
            args=(
                channel,
                method.delivery_tag,
                props,
                body["device"],
                body["method"],
                body["task_id"],
                *body["args"],
            ),
            kwargs=body["kwargs"],
        )
        self.threads.append(thread)
        thread.start()


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
        self._waiting: Dict[ObjectId, Future] = {}

        self._conn = get_rabbitmq_connection()
        self._channel = self._conn.channel()
        self._channel.queue_declare(
            self._rpc_reply_queue_name, exclusive=False, auto_delete=True
        )

        self._thread: Optional[Thread] = None

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

    def call(self, device_name: str, method: str, *args, **kwargs) -> Any:
        """
        Call a method inside the device with name ``device_name``. *args, **kwargs will be feeded into
        the method directly.

        Args:
            device_name: the name of device, which is defined by administer.
            method: the class method to call
            *args: positional arguments to feed into the method function
            **kwargs: keyword arguments to feed into the method function

        Returns
        -------
            the result of function
        """
        assert self._conn and self._channel

        f: Future = Future()
        correlation_id = ObjectId()
        self._waiting[correlation_id] = f
        self._conn.add_callback_threadsafe(
            lambda: self._channel.basic_publish(
                exchange="",
                routing_key=self._rpc_queue_name,
                body=dill.dumps(
                    {
                        "device": device_name,
                        "method": method,
                        "args": args,
                        "kwargs": kwargs,
                        "task_id": str(self._task_id),
                    }
                ),
                properties=BasicProperties(
                    reply_to=self._rpc_reply_queue_name,
                    content_type="application/python-dill",
                    correlation_id=str(correlation_id),
                ),
            )
        )
        return f.result()

    def on_message(
        self,
        channel: BlockingChannel,
        method_frame: Basic.Deliver,  # pylint: disable=unused-argument
        properties: BasicProperties,
        _body: bytes,
    ):
        """Callback function to handle a returned message from Device Manager."""
        body = dill.loads(_body)

        f = self._waiting.pop(ObjectId(properties.correlation_id))
        if body["status"] == "success":
            f.set_result(body["result"])
        else:
            f.set_exception(body["result"])
