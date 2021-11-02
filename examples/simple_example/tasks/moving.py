from dataclasses import dataclass

from alab_management.task_view.task import BaseTask


@dataclass
class Moving(BaseTask):
    dest: str

    def run(self):
        ...
