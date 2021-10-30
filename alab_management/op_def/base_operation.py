from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List, Tuple, Dict, Type

from bson import ObjectId

from alab_management.sample_position import SamplePositionPair


@dataclass
class BaseOperation(ABC):
    """
    The abstract class of operation.

    All the operations should inherit from this class.

    Attributes:
        task_id: the identifier of task
        sample_id: the id of sample to do operations on
    """
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
    def run(self, logger):
        """
        Run the task and return some data
        """
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


_operation_registry: Dict[str, Type[BaseOperation]] = {}


def add_operation(operation: Type[BaseOperation]):
    if operation.__name__ in _operation_registry:
        raise KeyError("Duplicated operation name {}".format(operation.__name__))
    _operation_registry[operation.__name__] = operation


def get_operation(name: str) -> Type[BaseOperation]:
    return _operation_registry[name]


def get_all_operations() -> Dict[str, Type[BaseOperation]]:
    return _operation_registry.copy()
