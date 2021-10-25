from enum import Enum, auto
from typing import Dict, Any

from bson import ObjectId

from alab_management.config import config
from alab_management.db import get_collection


class SamplePositionStatus(Enum):
    UNKNOWN = auto()
    EMPTY = auto()
    OCCUPIED = auto()
    LOCKED = auto()


class SampleView:
    def __init__(self):
        self._collection = get_collection(config["sample_positions"]["sample_db"])

    def update_sample_view(self, sample_id: ObjectId, position: str):
        ...

    def query_sample_id(self, sample_id: ObjectId) -> str:
        ...

    def query_sample_position_info(self, sample_id: ObjectId) -> Dict[str, Any]:
        ...

    def find_possible_path(self, from_: str, to_: str):
        ...

    def delete_sample(self, sample_id):
        ...
