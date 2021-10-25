"""
Generate device, sample position, task definitions from user defined files (task & device)
and write them to MongoDB, which will make it easier to query
"""

import inspect
from dataclasses import asdict, fields, Field
from typing import Iterable, Type, Any, Dict, List

import pymongo
from bson import ObjectId

from .cleanup_lab import clean_up_db
from ..config import config
from ..db import get_collection
from ..device_def.base_device import get_all_devices, BaseDevice
from ..lab_status.device_view import DeviceStatus
from ..lab_status.sample_view import SamplePositionStatus
from ..op_def.base_operation import BaseOperation, BaseMovingOperation
from ..sample_position import SamplePosition
from ..utils.fake_device import FakeDevice
from ..utils.module_ops import import_module_from_path, get_full_cls_name
from ..utils.typing_ops import is_typing


def add_sample_positions_to_db(collection: pymongo.collection.Collection,
                               sample_positions: Iterable[SamplePosition]):
    """
    Insert sample positions info to db, which includes position name,
    number, description and status (default to ``UNKNOWN``)

    If one sample position's name has already appeared in the database,
    we will just skip it.

    Args:
        collection: the db collection to store sample position data
        sample_positions: some sample position instances
    """
    for sample_pos in sample_positions:
        sample_pos_ = collection.find_one({"name": sample_pos.name})
        if sample_pos_ is None:
            collection.insert_one({
                **asdict(sample_pos),
                "status": SamplePositionStatus.UNKNOWN.name,
                "task_id": None,
                "sample_id": None,
            })


def add_devices_to_db(collection: pymongo.collection.Collection,
                      devices: Iterable[BaseDevice]):
    """
    Insert device definitions to db, which includes devices' name, descriptions, parameters,
    type (class name).

    When one device's name has already appeared in the database, a ``NameError`` will be raised.
    Device name is a unique identifier for a device

    Args:
        collection: the db collection to store device data
        devices: some devices inherited from :py:class:`BaseDevice <alab_management.device_def.base_device.BaseDevice>`
    """
    for device in devices:
        if collection.find_one({"name": device.name}) is not None:
            raise NameError(f"Duplicated device name {device.name}, did you cleanup the database?")
        collection.insert_one({
            "sample_positions": [sample_pos.name for sample_pos in device.sample_positions],
            "status": DeviceStatus.UNKNOWN.name,
            "type": device.__class__.__name__,
            "description": device.description,
            "task_id": None,
            "sample_id": None,
            **asdict(device),
        })


def setup_from_device_def():
    """
    Set up sample positions, devices from user's device definition, whose path is
    specified by ``config["devices"]["device_dir"]``
    """
    device_collection = get_collection(config["devices"]["device_db"])
    sample_position_collection = get_collection(config["sample_positions"]["sample_db"])

    device_collection.create_index([("name", pymongo.HASHED)])
    sample_position_collection.create_index([("name", pymongo.HASHED)])

    # import all the devices, which will execute `__init__.py` in the device dir
    # and call `add_device` function
    import_module_from_path(config["devices"]["device_dir"])

    # obtain all the devices
    devices = get_all_devices().values()

    add_devices_to_db(device_collection, devices)
    add_sample_positions_to_db(sample_position_collection, [sample_pos for device in devices
                                                            for sample_pos in device.sample_positions])


def init_with_fake_parameters(cls: Type[BaseOperation]) -> BaseOperation:
    """
    For task class, which need to be initialized to get the occupied positions
    and operation locations. We will initialized the task with a set of fake parameters
    based on their type annotations.

    We implemented these faking types:
        - :py:class:`BaseDevice <alab_management.device_def.base_device.BaseDevice>` -> FakeDevice with name = {{name}}
        - :py:class:`SamplePosition <alab_management.sample_position.SamplePosition>` -> SamplePosition with name = {{name}}
        - built-in types (can be nested) : ``int``, ``float``, ``str``, ``list``, ``dict``, ``set``

    .. note::
        Things like ``List[BaseDevice]`` and ``Dict[str, SamplePosition]`` are not
        supported up to now.

    Args:
        cls: the operation class to be initialized
    """
    type_hints = fields(cls)

    fake_parameters = {}
    for type_hint in type_hints:
        type_hint: Field
        name = type_hint.name
        type_ = type_hint.type

        if is_typing(type_):
            type_ = type_.__origin__

        if issubclass(type_, BaseDevice):
            fake_parameters[name] = FakeDevice(name="{" + type_.__name__ + "}")
        elif issubclass(type_, SamplePosition):
            fake_parameters[name] = SamplePosition(name="{" + name + "}", description="")
        else:
            fake_parameters[name] = type_()
    return cls(**fake_parameters)


def add_tasks_to_db(collection: pymongo.collection.Collection,
                    tasks: Iterable[BaseOperation]):
    """
    Insert task definitions to db, which includes tasks' name, operation location,
    (where the sample should be), occupied positions and accepted_args

    Args:
        collection: the collection that stores task definition data
        tasks: some tasks inherited from :py:class:`BaseDevice <alab_management.device_def.base_device.BaseDevice>`
    """
    for task in tasks:
        if collection.find_one({"name": task.__class__.__name__}) is not None:
            raise NameError(f"Duplicated task name: {task.__class__.__name__}")
        task_info = {
            "name": task.__class__.__name__,
            "operation_location": task.operation_location,
            "occupied_positions": task.occupied_positions,
            "dist_location": task.dest_location,
            "accepted_args": [{"name": field.name, "type": get_full_cls_name(field.type)} for field in fields(task)
                              if is_typing(field.type) or not issubclass(field.type, (BaseDevice, ObjectId))]
        }
        if isinstance(task, BaseMovingOperation):
            task_info.update({
                "src_dest_pairs": [{
                    "src": sample_position_pair.src,
                    "dest": sample_position_pair.dest,
                    "containers": sample_position_pair.containers,
                } for sample_position_pair in task.get_possible_src_dest_pairs()],
            })

        collection.insert_one(task_info)


def make_sample_position_graph():
    """
    From the moving operation's source and destination pairs,
    we can add edges to sample view, which can tell the system
    how to move samples between two places
    """
    task_collection = get_collection(config["tasks"]["task_db"])
    sample_position_collection = get_collection(config["sample_positions"]["sample_db"])

    next_positions_dict: Dict[str, List[Dict[str, Any]]] = {}
    for task in task_collection.find({"src_dest_pairs": {"$exists": True}}):
        for src_dest_pair in task["src_dest_pairs"]:
            next_positions_dict.setdefault(src_dest_pair["src"], [])
            next_positions_dict[src_dest_pair["src"]].extend([{
                "dest": src_dest_pair["dest"],
                "container": container,
                "task_name": task["name"],
            } for container in src_dest_pair["containers"]])

    for name, next_positions in next_positions_dict.items():
        if sample_position_collection.find_one({"name": name}) is None:
            raise ValueError(f"Sample position does not exist: {name}")
        sample_position_collection.update_one({"name": name}, {"$set": {
            "next_positions": next_positions,
        }})


def setup_from_task_def():
    """
    Set up sample positions' edges, task definitions from user's task definition, whose path is
    specified by ``config["tasks"]["task_dir"]``
    """
    task_collection = get_collection(config["tasks"]["task_db"])

    task_collection.create_index([("name", pymongo.HASHED)])
    tasks_cls = [var for var in import_module_from_path(config["tasks"]["task_dir"]).__dict__.values()
                 if inspect.isclass(var) and issubclass(var, BaseOperation)]

    tasks = [init_with_fake_parameters(task_cls) for task_cls in tasks_cls]
    add_tasks_to_db(task_collection, tasks)
    make_sample_position_graph()


def setup_lab():
    clean_up_db()
    setup_from_device_def()
    setup_from_task_def()
