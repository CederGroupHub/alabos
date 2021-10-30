from enum import Enum, auto
from typing import Optional

from bson import ObjectId

from alab_management.config import config
from alab_management.db import get_collection


class SampleView:
    def __init__(self):
        self._collection = get_collection(config["sample_positions"]["sample_db"])
        self._sample_position = get_collection(config["sample_positions"]["sample_position_db"])

    def create_sample(self) -> ObjectId:
        result = self._collection.insert_one({
            "position": None,
        })
        return result.inserted_id

    def update_sample_position(self, sample_id: ObjectId, new_position: str):
        if self._collection.find_one({"_id": sample_id}) is None:
            raise KeyError(f"Cannot find sample with id ({sample_id}).")
        self._collection.update_one({"_id": sample_id}, {"$set": {
            "position": new_position,
        }})

    def query_sample(self, sample_id: ObjectId) -> Optional[str]:
        sample = self._collection.find_one({"_id": sample_id})
        return sample["position"]

    def find_possible_path(self, src: str, dest: str, container: Optional[str]):
        ...

    def delete_sample(self, sample_id: ObjectId):
        if self._collection.find_one({"_id": sample_id}) is None:
            raise KeyError(f"Cannot find sample with id ({sample_id}).")
        self._collection.delete_one({"_id": sample_id})
