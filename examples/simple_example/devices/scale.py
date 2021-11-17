import time
from typing import ClassVar

import requests

from alab_management import BaseDevice, SamplePosition


class Scale(BaseDevice):
    description: ClassVar[str] = "Simple scale read data by camera"

    UPDATE_URL = "https://www.ocf.berkeley.edu/~yuxingfei/api/update"
    GET_URL = "https://www.ocf.berkeley.edu/~yuxingfei/api/get"

    @property
    def sample_positions(self):
        return [
            SamplePosition(
                f"{self.name}.inside",
                description="Where we weigh things"
            ),
        ]

    def emergent_stop(self):
        pass

    def read_data(self) -> bytes:
        requests.get(self.UPDATE_URL)
        time.sleep(1.5)
        return requests.get(self.GET_URL).content

    def is_running(self):
        return False
