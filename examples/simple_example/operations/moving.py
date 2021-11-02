from dataclasses import dataclass

from alab_management.task_manager.base_operation import BaseOperation


@dataclass
class Moving(BaseOperation):
    dest: str

    def run(self):
        ...
