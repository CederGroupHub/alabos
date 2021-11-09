import time
from dataclasses import asdict
from datetime import datetime
from enum import Enum, auto
from threading import Lock
from typing import Optional, List, Dict, Any, Tuple

import pymongo
from bson import ObjectId

from .sample import Sample
from ..db import get_collection


class SamplePositionStatus(Enum):
    EMPTY = auto()  # the sample position is neither locked nor occupied
    OCCUPIED = auto()  # there is a sample in the sample position
    LOCKED = auto()  # the sample position is locked by a task


class SamplePositionsLock:
    def __init__(self, sample_positions: Optional[Dict[str, str]], sample_view: "SampleView"):
        self._sample_positions = sample_positions
        self._sample_view = sample_view

    @property
    def sample_positions(self):
        return self._sample_positions

    def release(self):
        if self._sample_positions is not None:
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
        self._sample_positions_collection.create_index([("name", pymongo.HASHED,)])
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
        # TODO: support it!
        if len(sample_position) != len(set(sample_position)):
            raise ValueError("Currently we do not allow duplicated sample_positions in one request.")

        cnt = 0
        while timeout is None or cnt < timeout:
            try:
                self._lock.acquire(blocking=True)
                available_positions = {}
                for sp in sample_position:
                    result = self.get_available_sample_position(task_id, position_prefix=sp)
                    if not result:
                        break
                    available_positions[sp] = result[0]
                else:
                    for sp in available_positions.values():
                        self.lock_sample_position(task_id, sp)
                    return SamplePositionsLock(sample_positions=available_positions, sample_view=self)
            finally:
                self._lock.release()

            time.sleep(1)
            cnt += 1

        return SamplePositionsLock(sample_positions=None, sample_view=self)

    def get_sample_position(self, position: str) -> Optional[Dict[str, Any]]:
        """
        Get the sample position entry in the database

        if the position is not a valid position (not defined in the database), return None
        """
        return self._sample_positions_collection.find_one({"name": position})

    def get_sample_position_status(self, position: str) -> Tuple[SamplePositionStatus, Optional[ObjectId]]:
        """
        Get the status of a sample position

        If there is a sample in the position, return OCCUPIED;
        else if the sample position is locked by a task, return LOCKED;
        return EMPTY

        Args:
            position: the name of the sample position

        Returns:
            if the position is occupied by a sample, return OCCUPIED and the task id of the sample
            if the position is locked by a task, return LOCKED and the task id
            else, return EMPTY and None
        """
        sample_position = self._sample_positions_collection.find_one({"name": position})

        if sample_position is None:
            raise ValueError(f"Invalid sample position: {position}")

        sample = self._sample_collection.find_one({"position": position})
        if sample is not None:
            return SamplePositionStatus.OCCUPIED, sample["task_id"]

        if sample_position["task_id"] is not None:
            return SamplePositionStatus.LOCKED, sample_position["task_id"]

        return SamplePositionStatus.EMPTY, None

    def is_empty_position(self, position: str) -> bool:
        """
        Tell if a sample position is empty
        """
        return self.get_sample_position_status(position)[0] is SamplePositionStatus.EMPTY

    def get_available_sample_position(self, task_id: ObjectId, position_prefix: str) -> List[str]:
        """
        Check if the position is occupied
        """
        if self._sample_positions_collection.find_one({"name": {"$regex": f"^{position_prefix}"}}) is None:
            raise ValueError(f"Cannot find device with prefix: {position_prefix}")

        available_sample_positions = self._sample_positions_collection.find({
            "name": {"$regex": f"^{position_prefix}"},
            "$or": [{
                "task_id": None,
            }, {
                "task_id": task_id,
            }]}
        )
        available_sp_names = []
        for sp in available_sample_positions:
            status, current_task_id = self.get_sample_position_status(sp["name"])
            if status is SamplePositionStatus.EMPTY or task_id == current_task_id:
                available_sp_names.append(sp["name"])
        return available_sp_names

    def lock_sample_position(self, task_id: ObjectId, position: str):
        """
        Lock a sample position
        """
        sample_status, current_task_id = self.get_sample_position_status(position)

        if current_task_id != task_id:
            if sample_status is SamplePositionStatus.OCCUPIED:
                raise ValueError(f"Position ({position}) is currently occupied")
            elif sample_status is SamplePositionStatus.LOCKED:
                raise ValueError(f"Position is currently locked by task: {task_id}")

        self._sample_positions_collection.update_one({"name": position}, {"$set": {
            "task_id": task_id,
        }})

    def release_sample_position(self, position: str):
        """
        Unlock a sample position
        """
        if self.get_sample_position(position) is None:
            raise ValueError(f"Invalid sample position: {position}")

        self._sample_positions_collection.update_one({"name": position}, {"$set": {
            "task_id": None,
        }})

    #################################################################
    #                 operations related to samples                 #
    #################################################################

    def create_sample(self, name: str,
                      position: Optional[str] = None) -> ObjectId:
        """
        Create a sample and return its uid in the database

        Samples with the same name can exist in the database
        """
        if position is not None and not self.is_empty_position(position):
            raise ValueError(f"Requested position ({position}) is not EMPTY.")

        result = self._sample_collection.insert_one({
            "name": name,
            "position": position,
            "task_id": None,
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
            return Sample(_id=result["_id"], name=result["name"], position=result["position"])
        else:
            return None

    def update_sample_task_id(self, sample_id: ObjectId, task_id: Optional[ObjectId]):
        """
        Update the task id for a sample
        """
        result = self._sample_collection.find_one({"_id": sample_id})
        if result is None:
            raise ValueError(f"Cannot find sample with id: {sample_id}")

        self._sample_collection.update_one({"_id": sample_id}, {"$set": {
            "task_id": task_id,
            "last_updated": datetime.now(),
        }})

    def move_sample(self, sample_id: ObjectId, position: Optional[str]):
        """
        Update the sample with new position
        """
        result = self._sample_collection.find_one({"_id": sample_id})
        if result is None:
            raise ValueError(f"Cannot find sample with id: {sample_id}")

        if position is not None and not self.is_empty_position(position):
            raise ValueError(f"Requested position ({position}) is not EMPTY.")

        self._sample_collection.update_one({"_id": sample_id}, {"$set": {
            "position": position,
            "last_updated": datetime.now(),
        }})
