from dataclasses import dataclass

from alab_management.task_view.task import BaseTask


@dataclass
class Moving(BaseTask):
    LONG_TIME_TASK = False

    def __init__(self, dest: str, *args, **kwargs):
        super(Moving, self).__init__(*args, **kwargs)
        self.dest = dest

    def run(self):
        ...
