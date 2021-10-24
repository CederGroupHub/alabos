from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List

from bson import ObjectId


@dataclass
class BaseOperation(ABC):
    task_id: ObjectId = field(hash=False, compare=False)
    sample_id: ObjectId = field(hash=False, compare=False)

    @abstractmethod
    @property
    def operation_location(self) -> str:
        raise NotImplementedError()

    @abstractmethod
    def __call__(self):
        raise NotImplementedError()

    @abstractmethod
    def is_running(self) -> bool:
        raise NotImplementedError()

    @property
    def dest_location(self) -> str:
        return self.operation_location

    @property
    def occupied_positions(self) -> List[str]:
        return []
