"""
Executor is the core module of
"""

import threading
import time
from typing import Any, Dict

from alab_management.device_view import DeviceView
from alab_management.logger import DBLogger
from alab_management.sample_view.sample_view import SampleView
from alab_management.task_view.task_view import TaskView, TaskStatus
from alab_management.utils.module_ops import load_definition


class ParameterError(Exception):
    """
    The exception raised when parameters of a task is wrong
    """


class Executor:
    """
    Executor find all the ready tasks and submit them
    """
    def __init__(self):
        load_definition()
        self.device_view = DeviceView()
        self.sample_view = SampleView()
        self.task_view = TaskView()

    def run(self):
        """
        The main function that
        Returns:

        """
        while True:
            self._loop()
            time.sleep(1)

    def _loop(self):
        ready_task_entries = self.task_view.get_ready_tasks()
        for task_entry in ready_task_entries:
            self.submit_task(task_entry)

    def submit_task(self, task_entry: Dict[str, Any]):
        task_id = task_entry["task_id"]
        task_type = task_entry.pop("type")
        logger = DBLogger(task_id=task_id)
        try:
            task = task_type(
                logger=logger,
                device_view=self.device_view,
                sample_view=self.sample_view,
                **task_entry,
            )
        except AttributeError as e:
            raise ParameterError(e.args[0])

        def _run_task():
            self.task_view.update_status(task_id=task_id, status=TaskStatus.RUNNING)
            try:
                task.run()
            except Exception:
                self.task_view.update_status(task_id=task_id, status=TaskStatus.ERROR)
                raise
            else:
                self.task_view.update_status(task_id=task_id, status=TaskStatus.COMPLETED)

        task_thread = threading.Thread(target=_run_task)
        task_thread.start()
