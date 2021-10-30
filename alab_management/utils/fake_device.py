from dataclasses import dataclass

from ..device_def import BaseDevice


@dataclass
class FakeDevice(BaseDevice):
    """
    Fake device for setting up the lab's db
    """
    @property
    def sample_positions(self): return []
    def init(self): ...
