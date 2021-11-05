import time
from dataclasses import asdict
from datetime import datetime
from threading import Lock
from typing import Optional, List, Dict, Any

import pymongo
from bson import ObjectId

from .sample import Sample
from ..db import get_collection


class SamplePositionsLock:
    def __init__(self, sample_positions: Dict[str, str], sample_view: "SampleView"):
        self._sample_positions = sample_positions
        self._sample_view = sample_view

    @property
    def sample_positions(self):
        return self._sample_positions

    def release(self):
        for sample_position in self._sample_positions.values():
            self._sample_view.release_sample_position(sample_position)

    def __enter__(self):
        return self.sample_positions

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.release()


class SampleView:
    """
    Sample view manages the samples and their positions
    """

    def __init__(self):
        self._sample_collection = get_collection("samples")
        self._sample_positions_collection = get_collection("sample_positions")
        self._sample_positions_collection.create_index([("name", pymongo.HASHED)])
        self._lock = Lock()

    def add_sample_positions_to_db(self, sample_positions):
        """
        Insert sample positions info to db, which includes position name and description

        If one sample position's name has already appeared in the database,
        we will just skip it.

        Args:
            sample_positions: some sample position instances
        """
        for sample_pos in sample_positions:
            sample_pos_ = self._sample_positions_collection.find_one({"name": sample_pos.name})
            if sample_pos_ is None:
                self._sample_positions_collection.insert_one({
                    "occupied": False,
                    "task_id": None,
                    "last_updated": datetime.now(),
                    **asdict(sample_pos)
                })

    def clean_up_sample_position_collection(self):
        """
        Drop the sample position collection
        """
        self._sample_positions_collection.drop()

    def request_sample_positions(self, task_id: ObjectId, *sample_position: str,
                                 timeout: Optional[int] = None) -> Optional[SamplePositionsLock]:
        if len(sample_position) != len(set(sample_position)):
            raise ValueError("Currently we do not allow duplicated sample_positions in one request.")

        cnt = 0
        while timeout is None or cnt < timeout:
            try:
                self._lock.acquire(blocking=True)
                available_positions = {}
                for sp in sample_position:
                    result = self.get_available_sample_position(task_id, sp)
                    if not result:
                        break
                    available_positions[sp] = result[0]
                else:
                    for sp in available_positions.values():
                        self.occupy_sample_position(task_id, sp)
                    return SamplePositionsLock(sample_positions=available_positions, sample_view=self)
            finally:
                self._lock.release()

            time.sleep(1)
            cnt += 1

    def get_sample_position(self, position: str) -> Optional[Dict[str, Any]]:
        return self._sample_positions_collection.find_one({"name": position})

    def is_valid_position(self, position: str) -> bool:
        """
        Tell if a sample position is valid in the database
        """
        return self.get_sample_position(position) is not None

    def get_available_sample_position(self, task_id: ObjectId, position: str) -> List[str]:
        """
        Check if the position is occupied
        """
        if self._sample_positions_collection.find_one({"position": {"$regex": f"^{position}"}}) is None:
            raise ValueError(f"Cannot find device with prefix: {position}")

        available_sample_positions = self._sample_positions_collection.find(
            {"name": f"^{position}",
             "$or": [{
                 "occupied": False,
             }, {
                 "task_id": task_id,
             }]})

        return [sp["name"] for sp in available_sample_positions]

    def occupy_sample_position(self, task_id: ObjectId, position: str):
        if not self.is_valid_position(position):
            raise ValueError(f"Invalid sample position: {position}")
        if self.get_sample_position(position)["occupied"]:
            raise ValueError(f"Requested sample position has been occupied: {position}.")
        self._sample_positions_collection.update_one({"name": position}, {"$set": {
            "occupied": True,
            "task_id": task_id,
        }})

    def release_sample_position(self, position: str):
        if not self.is_valid_position(position):
            raise ValueError(f"Invalid sample position: {position}")

        self._sample_positions_collection.update_one({"name": position}, {"$set": {
            "occupied": False,
            "task_id": None,
        }})

    def create_sample(self, name: str,
                      position: Optional[str] = None) -> ObjectId:
        """
        Create a sample and return its uid in the database
        """
        if position is not None and not self.is_valid_position(position):
            raise ValueError(f"Unknown position name: {position}")

        result = self._sample_collection.insert_one({
            "name": name,
            "position": position,
            "created_at": datetime.now(),
            "last_updated": datetime.now(),
        })

        return result.inserted_id

    def get_sample(self, sample_id: ObjectId) -> Optional[Sample]:
        """
        Get a sample by sample_id
        """
        result = self._sample_collection.find_one({"_id": sample_id})
        if result is not None:
            return Sample(**result)
        return None

    def move_sample(self, sample_id: ObjectId, position: Optional[str]):
        """
        update the sample with new position
        """
        result = self._sample_collection.find_one({"_id": sample_id})
        if result is None:
            raise ValueError(f"Cannot find sample with id: {sample_id}")

        if position is not None and not self.is_valid_position(position):
            raise ValueError(f"Unknown position name: {position}")

        self._sample_collection.update_one({"_id": sample_id}, {"$set": {
            "position": position,
            "last_updated": datetime.now(),
        }})
