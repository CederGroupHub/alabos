from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List, Tuple

from bson import ObjectId


@dataclass
class BaseOperation(ABC):
    task_id: ObjectId = field(hash=False, compare=False)
    sample_id: ObjectId = field(hash=False, compare=False)

    @property
    @abstractmethod
    def operation_location(self) -> str:
        raise NotImplementedError()

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
    @property
    @abstractmethod
    def possible_src_dest(self) -> List[Tuple[str, str]]:
        raise NotImplementedError()
