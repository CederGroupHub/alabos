from collections import Iterable
from dataclasses import asdict
from enum import Enum, unique, auto
from typing import Optional

import pymongo
from bson import ObjectId

from alab_management.config import config
from alab_management.db import get_collection
from alab_management.sample_manager.sample import SamplePosition, Sample


@unique
class SampleStatus(Enum):
    UNKNOWN = auto()
    PENDING = auto()
    LOCKED = auto()


class SampleView:
    """
    Sample view manages the samples and their positions
    """

    def __init__(self):
        self._sample_collection = get_collection(config["sample_positions"]["sample_db"])
        self._sample_positions_collection = get_collection(config["sample_positions"]["sample_db"] + "_position")
        self._sample_positions_collection.create_index([("name", pymongo.HASHED)])

    def add_sample_positions_to_db(self, sample_positions: Iterable[SamplePosition]):
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
                self._sample_positions_collection.insert_one(asdict(sample_pos))

    def is_valid_position(self, position: str) -> bool:
        """
        Tell if a sample position is a valid position in the database
        """
        return self._sample_positions_collection.find_one({"name": position}) is not None

    def create_sample(self, position: Optional[str] = None) -> ObjectId:
        """
        Create a sample and return its uid in the database
        """
        if position is not None and not self.is_valid_position(position):
            raise ValueError(f"Unknown position name: {position}")

        result = self._sample_collection.insert_one({
            "position": position,
        })

        return result.inserted_id

    def get_sample(self, sample_id: ObjectId) -> Sample:
        """
        Get a sample by sample_id
        """
        result = self._sample_collection.find_one({"_id": sample_id})
        if result is None:
            raise ValueError(f"Cannot find sample with id: {sample_id}")
        return Sample(**result)

    def update_sample_position(self, sample_id: ObjectId, position: Optional[str]):
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
        }})
