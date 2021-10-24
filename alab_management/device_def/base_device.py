from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List, ClassVar, Dict

from .sample_position import SamplePosition


@dataclass
class BaseDevice(ABC):
    name: str
    description: ClassVar[str] = ""

    @abstractmethod
    def init(self):
        raise NotImplementedError()

    @property
    @abstractmethod
    def sample_positions(self) -> List[SamplePosition]:
        raise NotImplementedError()


_device_registry: Dict[str, BaseDevice] = {}


def add_device(device: BaseDevice):
    if device.name in _device_registry:
        raise KeyError("Duplicated device name {}".format(device.name))
    _device_registry[device.name] = device


def get_device(name: str):
    return _device_registry[name]


def get_all_devices() -> Dict[str, BaseDevice]:
    return _device_registry.copy()
