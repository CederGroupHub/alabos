from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List, Tuple

from bson import ObjectId

from alab_management.sample_position import SamplePositionPair


@dataclass
class BaseOperation(ABC):
    task_id: ObjectId = field(hash=False, compare=False)
    sample_id: ObjectId = field(hash=False, compare=False)

    @property
    @abstractmethod
    def operation_location(self) -> str:
        raise NotImplementedError()

    @property
    def dest_location(self) -> str:
        return self.operation_location

    @abstractmethod
    def __call__(self):
        raise NotImplementedError()

    @abstractmethod
    def is_running(self) -> bool:
        raise NotImplementedError()

    @property
    def occupied_positions(self) -> List[str]:
        return []


@dataclass
class BaseMovingOperation(BaseOperation, ABC):
    @staticmethod
    @abstractmethod
    def get_possible_src_dest_pairs() -> Tuple[SamplePositionPair]:
        raise NotImplementedError()

    @property
    @abstractmethod
    def dest_location(self):
        raise NotImplementedError()
