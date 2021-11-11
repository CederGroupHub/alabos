"""
Executor is the core module of the system,
which actually executes the tasks
"""

import threading
import time
from typing import Any, Dict

from bson import ObjectId

from .device_view import DeviceView
from .lab_manager import LabManager
from .logger import DBLogger
from .sample_view.sample_view import SampleView
from .task_view.task_view import TaskView, TaskStatus
from .utils.module_ops import load_definition


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
        while True:
            self._loop()
            time.sleep(1)

    def _loop(self):
        ready_task_entries = self.task_view.get_ready_tasks()
        for task_entry in ready_task_entries:
            self.submit_task(task_entry)

    def submit_task(self, task_entry: Dict[str, Any]):
        """
        Submit a task. In this system, each task is run in an
        independent thread, which will try to acquire device and
        process samples.
        """
        task_id = task_entry["task_id"]
        task_type = task_entry.pop("type")
        logger = DBLogger(task_id=task_id)
        lab_manager = LabManager(device_view=self.device_view, sample_view=self.sample_view, task_id=task_id)
        try:
            task = task_type(
                logger=logger,
                lab_manager=lab_manager,
                **task_entry["samples"],
                **task_entry["parameters"],
            )
        except AttributeError as e:
            raise ParameterError(e.args[0])

        def _run_task():
            self.task_view.update_status(task_id=task_id, status=TaskStatus.RUNNING)
            for sample_id in task_entry["samples"]:
                self.sample_view.update_sample_task_id(task_id=task_id, sample_id=sample_id)
            try:
                task.run()
            except Exception:
                self.task_view.update_status(task_id=task_id, status=TaskStatus.ERROR)
                raise
            else:
                self.task_view.update_status(task_id=task_id, status=TaskStatus.COMPLETED)
            finally:
                for sample_id in task_entry["samples"]:
                    self.sample_view.update_sample_task_id(task_id=None, sample_id=sample_id)

        task_thread = threading.Thread(target=_run_task)
        task_thread.start()
