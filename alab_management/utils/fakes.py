from dataclasses import dataclass

from ..device_def import BaseDevice


@dataclass
class FakeDevice(BaseDevice):
    @property
    def sample_positions(self): return []
    def init(self): ...
