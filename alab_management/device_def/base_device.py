from abc import ABC, abstractmethod
from typing import List

from .sample_position import SamplePosition


class BaseDevice(ABC):
    description = ""

    @abstractmethod
    @property
    def sample_positions(self) -> List[SamplePosition]:
        raise NotImplementedError()

    def __init__(self, name: str):
        self.name = name
