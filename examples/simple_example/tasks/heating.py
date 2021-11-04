from typing import List, Tuple

from alab_management import BaseTask


class Heating(BaseTask):
    def __init__(self, setpoints: List[Tuple[float, float]], *args, **kwargs):
        super(Heating, self).__init__(*args, **kwargs)
        self.setpoints = setpoints

    def run(self):
        ...