import time
from dataclasses import asdict
from datetime import datetime
from enum import Enum, auto
from threading import Lock
from typing import Optional, List, Dict, Any, Tuple, Collection

import pymongo
from bson import ObjectId

from .sample import Sample
from ..db import get_collection


class SamplePositionStatus(Enum):
    """
    The status of a sample position

    - ``EMPTY``: the sample position is neither locked nor occupied
    - ``OCCUPIED``: there is a sample in the sample position
    - ``LOCKED``: the sample position is reserved by a task
    """
    EMPTY = auto()
    OCCUPIED = auto()
    LOCKED = auto()


class SamplePositionsLock:
    """
    Lock of sample position, which is a context manager that will release the sample positions
    when exiting.
    """

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

    def request_sample_positions(self, task_id: ObjectId,
                                 sample_positions: Collection[str],  # pylint: disable=unsubscriptable-object
                                 timeout: Optional[int] = None) -> SamplePositionsLock:
        """
        Request a list of sample positions, this function will return until all the sample positions are available

        Args:
            task_id: the task id that requests these resources
            sample_positions: the list of sample positions, which is requested by their names.
              The sample position name is actually the prefix of a sample position, which we
              will try to match all the sample positions will the name
            timeout: if we cannot request the resources after ``timeout`` seconds, this function
              will return ``SamplePositionsLock(None)`` directly.
        """
        # TODO: support it!
        if len(sample_positions) != len(set(sample_positions)):
            raise ValueError("Currently we do not allow duplicated sample_positions in one request.")

        cnt = 0
        while timeout is None or cnt < timeout:
            try:
                self._lock.acquire(blocking=True)  # pylint: disable=consider-using-with
                available_positions = {}
                for sample_position_prefix in sample_positions:
                    result = self.get_available_sample_position(task_id, position_prefix=sample_position_prefix)
                    if not result:
                        break
                    available_positions[sample_position_prefix] = result[0]
                else:
                    for sample_position in available_positions.values():
                        self.lock_sample_position(task_id, sample_position)
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

    def is_unoccupied_position(self, position: str) -> bool:
        """
        Tell if a sample position is unoccupied or not
        """
        return not self.get_sample_position_status(position)[0] is SamplePositionStatus.OCCUPIED

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
        for sample_position in available_sample_positions:
            status, current_task_id = self.get_sample_position_status(sample_position["name"])
            if status is SamplePositionStatus.EMPTY or task_id == current_task_id:
                available_sp_names.append(sample_position["name"])
        return available_sp_names

    def lock_sample_position(self, task_id: ObjectId, position: str):
        """
        Lock a sample position
        """
        sample_status, current_task_id = self.get_sample_position_status(position)

        if current_task_id != task_id:
            if sample_status is SamplePositionStatus.OCCUPIED:
                raise ValueError(f"Position ({position}) is currently occupied")
            if sample_status is SamplePositionStatus.LOCKED:
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
        if position is not None and not self.is_unoccupied_position(position):
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

        if position is not None and not self.is_unoccupied_position(position):
            raise ValueError(f"Requested position ({position}) is not EMPTY or LOCKED by other task.")

        self._sample_collection.update_one({"_id": sample_id}, {"$set": {
            "position": position,
            "last_updated": datetime.now(),
        }})
