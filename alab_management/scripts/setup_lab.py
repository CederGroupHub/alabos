import inspect
from dataclasses import asdict, fields, Field
from typing import Iterable, Type

import pymongo

from ..config import config
from ..db import get_collection
from ..device_def import SamplePosition
from ..device_def.base_device import get_all_devices, BaseDevice
from ..lab_status.device_view import DeviceStatus
from ..lab_status.sample_view import SamplePositionStatus
from ..op_def.base_operation import BaseOperation, BaseMovingOperation
from ..utils.fakes import FakeDevice
from ..utils.module_op import import_module_from_path


def add_sample_positions_to_db(collection: pymongo.collection.Collection,
                               sample_positions: Iterable[SamplePosition]):
    for sample_pos in sample_positions:
        pos_num = sample_pos.num

        sample_pos_ = collection.find_one({"name": sample_pos.name})
        if sample_pos_ is not None:
            if pos_num != sample_pos_["num"]:
                raise ValueError("Inconsistent sample capacity for same position ({}): {} and "
                                 "{}".format(sample_pos.name, pos_num, sample_pos_["num"]))
        else:
            collection.insert_one({
                **asdict(sample_pos),
                "status": [SamplePositionStatus.UNKNOWN.name] * pos_num,
                "task_ids": [None] * pos_num,
                "sample_ids": [None] * pos_num,
            })


def add_devices_to_db(collection: pymongo.collection.Collection,
                      devices: Iterable[BaseDevice]):
    for device in devices:
        if collection.find_one({"name": device.name}) is not None:
            raise NameError("Duplicated device name {}, did you cleanup the database?".format(device.name))
        collection.insert_one({
            "sample_positions": [{"name": sample_pos.name, "num": sample_pos.num}
                                 for sample_pos in device.sample_positions],
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

        if hasattr(type_, "__origin__"):
            type_ = type_.__origin__

        if issubclass(type_, BaseDevice):
            fake_parameters[name] = FakeDevice(name="{" + type_.__name__ + "}")
        elif issubclass(type_, SamplePosition):
            fake_parameters[name] = SamplePosition(name="{" + name + "}", description="", num=1)
        else:
            fake_parameters[name] = type_()
    return cls(**fake_parameters)


def add_tasks_to_db(collection: pymongo.collection.Collection,
                    tasks: Iterable[BaseOperation]):
    for task in tasks:
        if collection.find_one({"name": task.__class__.__name__}) is not None:
            raise NameError("Duplicated task name: {}".format(task.__class__.__name__))
        task_info = {
            "name": task.__class__.__name__,
            "operation_location": task.operation_location,
            "occupied_positions": task.occupied_positions,
            "accept_args": ...  # TODO: finish this
        }
        if isinstance(task, BaseMovingOperation):
            task_info.update({
                "src_dest_pairs": task.possible_src_dest,
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
    setup_from_device_def()
    setup_from_task_def()
