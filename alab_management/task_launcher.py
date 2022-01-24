"""
TaskLauncher is the core module of the system,
which actually executes the tasks
"""

import threading
import time
from traceback import format_exc
from typing import Any, Dict

from .device_view import DeviceView
from .lab_manager import LabManager
from .logger import DBLogger
from .sample_view.sample_view import SampleView
from .task_view.task import BaseTask
from .task_view.task_view import TaskView, TaskStatus
from .utils.module_ops import load_definition


class ParameterError(Exception):
    """
    The exception raised when parameters of a task is wrong
    """


class TaskLauncher:
    """
    TaskLauncher find all the ready tasks and submit them
    """

    def __init__(self):
        load_definition()
        self.device_view = DeviceView()
        self.sample_view = SampleView()
        self.task_view = TaskView()
        self.logger = DBLogger(task_id=None)  # system log

        # init
        self.device_view.sync_device_status()

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
            self.submit_task(task_entry)

    def submit_task(self, task_entry: Dict[str, Any]):
        """
        Submit a task. In this system, each task is run in an
        independent thread, which will try to acquire device and
        process samples.
        """
        task_id = task_entry["task_id"]
        task_type = task_entry.pop("type")

        try:
            task: BaseTask = task_type(
                task_id=task_id,
                lab_manager=LabManager(task_id=task_id),
                **task_entry["samples"],
                **task_entry["parameters"],
            )
        except AttributeError as exception:
            raise ParameterError(exception.args[0]) from exception

        def _run_task():
            self.task_view.update_status(task_id=task_id, status=TaskStatus.RUNNING)
            for sample_id in task_entry["samples"].values():
                self.sample_view.update_sample_task_id(task_id=task_id, sample_id=sample_id)

            try:
                task.run()
            except Exception:
                self.task_view.update_status(task_id=task_id, status=TaskStatus.ERROR)
                self.logger.system_log(level="ERROR",
                                       log_data={
                                           "logged_by": self.__class__.__name__,
                                           "type": "TaskEnd",
                                           "task_id": task_id,
                                           "task_type": task_type.__name__,
                                           "status": "ERROR",
                                           "traceback": format_exc(),
                                       })
                raise
            else:
                self.task_view.update_status(task_id=task_id, status=TaskStatus.COMPLETED)
                self.logger.system_log(level="INFO",
                                       log_data={
                                           "logged_by": self.__class__.__name__,
                                           "type": "TaskEnd",
                                           "task_id": task_id,
                                           "task_type": task_type.__name__,
                                           "status": "COMPLETED",
                                       })
            finally:
                for sample_id in task_entry["samples"].values():
                    self.sample_view.update_sample_task_id(task_id=None, sample_id=sample_id)

        task_thread = threading.Thread(target=_run_task, name=str(task_id))
        task_thread.start()
        self.logger.system_log(level="INFO",
                               log_data={
                                   "type": "TaskStart",
                                   "task_id": task_id,
                                   "task_type": task_type.__name__
                               })
