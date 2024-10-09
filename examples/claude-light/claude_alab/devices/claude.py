import json
import requests
from typing import ClassVar

from alab_management.device_view import BaseDevice
from alab_management.sample_view import SamplePosition


class ClaudeLight(BaseDevice):
    """Claude Light definition"""
    description: ClassVar[str] = "Claude-Light device"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.running = None

    def __str__(self):
        return 'An RGB Claude Light'

    @property
    def sample_positions(self):
        """Sample positions define the sample positions related to this device."""
        return [
            SamplePosition(
                name="DefaultSamplePosition",
                number=1,
                description="Default sample position",
            )
        ]

    def connect(self):
        self.running = True

    def disconnect(self):
        self.running = False

    def is_running(self):
        return self.running

    def measure(self, R=0, G=0, B=0):
        resp = requests.get('https://claude-light.cheme.cmu.edu/api',
                            params={'R': R, 'G': G, 'B': B})
        data = resp.json()
        return data
