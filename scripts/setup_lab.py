from dataclasses import asdict
from pathlib import Path

import pymongo

from alab_management.config import config
from alab_management.db import get_collection
from alab_management.device_def.base_device import get_all_devices
from alab_management.lab_status.device_view import DeviceStatus
from alab_management.lab_status.sample_view import SamplePositionStatus


def setup_device_and_positions():
    import sys
    import importlib

    device_collection = get_collection(config["devices"]["device_db"])
    sample_position_collection = get_collection(config["sample_positions"]["sample_db"])

    device_collection.create_index([("name", pymongo.HASHED)])
    sample_position_collection.create_index([("name", pymongo.HASHED)])

    sys.path.append(Path(config["devices"]["device_dir"]).parent.as_posix())
    importlib.import_module("devices")

    devices = get_all_devices()

    for device in devices.values():
        if device_collection.find_one({"name": device.name}) is not None:
            raise NameError("Duplicated device name {}, did you cleanup the database?".format(device.name))
        device_collection.insert_one({
            "sample_positions": [{"name": sample_pos.name, "num": sample_pos.num}
                                 for sample_pos in device.sample_positions],
            "status": DeviceStatus.UNKNOWN.name,
            "type": device.__class__.__name__,
            "description": device.description,
            "task_id": None,
            "sample_id": None,
            **asdict(device),
        })
        for sample_pos in device.sample_positions:
            pos_num = sample_pos.num

            sample_pos_ = sample_position_collection.find_one({"name": sample_pos.name})
            if sample_pos_ is not None:
                if pos_num != sample_pos_["num"]:
                    raise ValueError("Inconsistent sample capacity for same position ({}): {} and "
                                     "{}".format(sample_pos.name, pos_num, sample_pos_["num"]))
                else:
                    continue

            sample_position_collection.insert_one({
                **asdict(sample_pos),
                "status": [SamplePositionStatus.UNKNOWN.name] * pos_num,
                "task_ids": [None] * pos_num,
                "sample_ids": [None] * pos_num,
            })


if __name__ == '__main__':
    setup_device_and_positions()
