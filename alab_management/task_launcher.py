"""
TaskLauncher is the core module of the system,
which actually executes the tasks
"""

import time

from .task_actor import run_task
from .task_view.task_view import TaskView
from .utils.module_ops import load_definition


class TaskLauncher:
    """
    TaskLauncher find all the ready tasks and submit them
    """

    def __init__(self):
        load_definition()
        self.task_view = TaskView()

    def run(self):
        """
        Start the loop
        """
        while True:
            self._loop()
            time.sleep(1)

    def _loop(self):
        ready_task_entries = self.task_view.get_ready_tasks()
        for task_entry in ready_task_entries:
            run_task.send(task_id_str=str(task_entry["task_id"]))
