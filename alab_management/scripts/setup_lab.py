"""
Setup the lab,

Generate device, sample position, task definitions from user defined files (task & device)
and write them to MongoDB
"""

import inspect
from dataclasses import asdict, fields, Field
from typing import Iterable, Type

import pymongo
from bson import ObjectId

from .cleanup_lab import clean_up_db
from ..config import config
from ..db import get_collection
from ..sample_position import SamplePosition
from ..device_def.base_device import get_all_devices, BaseDevice
from ..lab_status.device_view import DeviceStatus
from ..lab_status.sample_view import SamplePositionStatus
from ..op_def.base_operation import BaseOperation, BaseMovingOperation
from ..utils.fake_device import FakeDevice
from ..utils.module_ops import import_module_from_path, get_full_cls_name
from ..utils.typing_ops import is_typing


def add_sample_positions_to_db(collection: pymongo.collection.Collection,
                               sample_positions: Iterable[SamplePosition]):
    """
    Insert sample positions info to db, which includes position name,
    number, description and status (default to UNKNOWN)

    If one sample position's name has already appeared in the database, we will just skip it.

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
                "task_ids": None,
                "sample_ids": None,
            })


def add_devices_to_db(collection: pymongo.collection.Collection,
                      devices: Iterable[BaseDevice]):
    """
    Insert device definitions to db, which includes devices' name, descriptions, parameters,
    type (class name).

    When one device's name has already appeared in the database, a `NameError` will be raised.
    Device name is a unique identifier for a device

    Args:
        collection: the db collection to store device data
        devices: some devices inherited from :obj:`BaseDevice`
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
    device_collection = get_collection(config["devices"]["device_db"])
    sample_position_collection = get_collection(config["sample_positions"]["sample_db"])

    device_collection.create_index([("name", pymongo.HASHED)])
    sample_position_collection.create_index([("name", pymongo.HASHED)])

    import_module_from_path(config["devices"]["device_dir"])

    devices = get_all_devices().values()

    add_devices_to_db(device_collection, devices)
    add_sample_positions_to_db(sample_position_collection, [sample_pos for device in devices
                                                            for sample_pos in device.sample_positions])


def init_with_fake_parameters(cls: Type[BaseOperation]):
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
    for task in tasks:
        if collection.find_one({"name": task.__class__.__name__}) is not None:
            raise NameError(f"Duplicated task name: {task.__class__.__name__}")
        task_info = {
            "name": task.__class__.__name__,
            "operation_location": task.operation_location,
            "occupied_positions": task.occupied_positions,
            "dist_location": task.dest_location,
            "accept_args": [{"name": field.name, "type": get_full_cls_name(field.type)} for field in fields(task)
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


def setup_from_task_def():
    task_collection = get_collection(config["tasks"]["task_db"])

    task_collection.create_index([("name", pymongo.HASHED)])
    tasks_cls = [var for var in import_module_from_path(config["tasks"]["task_dir"]).__dict__.values()
                 if inspect.isclass(var) and issubclass(var, BaseOperation)]

    tasks = [init_with_fake_parameters(task_cls) for task_cls in tasks_cls]
    add_tasks_to_db(task_collection, tasks)


def main():
    clean_up_db()
    setup_from_device_def()
    setup_from_task_def()
