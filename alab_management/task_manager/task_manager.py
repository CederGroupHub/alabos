"""
TaskLauncher is the core module of the system,
which actually executes the tasks.
"""

import logging
import time
from contextlib import contextmanager

from dramatiq_abort import abort, abort_requested

from alab_management.lab_view import LabView
from alab_management.logger import DBLogger
from alab_management.task_view import TaskView
from alab_management.task_view.task_enums import CancelingProgress, TaskStatus
from alab_management.task_view.wait_messages import WORKER_QUEUE_MESSAGE
from alab_management.utils.module_ops import load_definition

cli_logger = logging.getLogger(__name__)


class TaskManager:
    """
    TaskManager will.

    (1) find all the ready tasks and submit them,
    (2) handle all the resource requests
    """

    def __init__(self):
        load_definition()
        self.task_view = TaskView()

        self.logger = DBLogger(task_id=None)
        self._pause_new_task_launching = False
        super().__init__()
        time.sleep(1)  # allow some time for other modules to launch

    @contextmanager
    def pause_new_task_launching(self):
        """Context manager to pause new task launching."""
        try:
            self._pause_new_task_launching = True
            cli_logger.info("Pausing new task launching.")
            yield
        finally:
            self._pause_new_task_launching = False
            cli_logger.info("Resuming new task launching.")

    def check_number_of_running_tasks(self) -> int:
        """Check the number of running tasks."""
        running_tasks = self.task_view.get_tasks_by_status(TaskStatus.RUNNING)
        return len(running_tasks)

    def run(self):
        """Start the loop."""
        while True:
            self._loop()
            time.sleep(1)

    def _loop(self):
        self.handle_tasks_to_be_canceled()
        if not self._pause_new_task_launching:
            self.submit_ready_tasks()

    def clean_up_tasks_from_previous_runs(self):
        """Arm cleanup for leftover RUNNING / REQUESTING_RESOURCES tasks without blocking.

        INITIATED tasks are requeued to READY immediately. For each dangling task a
        dashboard restart-cleanup prompt is posted; device/sample locks stay held until
        the operator OKs that prompt (handled by the dashboard completer). Dramatiq can
        start consuming other work right away.

        This typically occurs if workers were exited (SIGTERM / crash) while tasks were
        still RUNNING or REQUESTING_RESOURCES.
        """
        statuses_to_cancel = [
            TaskStatus.RUNNING,
            TaskStatus.REQUESTING_RESOURCES,
        ]
        tasks_to_cancel = []
        for status in statuses_to_cancel:
            tasks_to_cancel += self.task_view.get_tasks_by_status(status)

        statuses_to_restart = [TaskStatus.INITIATED]
        tasks_to_restart = []
        for status in statuses_to_restart:
            tasks_to_restart += self.task_view.get_tasks_by_status(status)

        for task in tasks_to_restart:
            self.task_view.update_status(
                task_id=task["task_id"], status=TaskStatus.READY
            )

        if len(tasks_to_cancel) == 0:
            cli_logger.info("No dangling tasks found from previous alabos workers. Nice!")
            return

        n = len(tasks_to_cancel)
        cli_logger.info(
            f"Found {n} dangling task(s) leftover from previous alabos workers. "
            "They were RUNNING or REQUESTING_RESOURCES when the workers stopped."
        )
        cli_logger.info(
            "Posting dashboard cleanup prompts (non-blocking). Locks stay held until "
            "each prompt is acknowledged; workers start immediately so other experiments "
            "can run on free resources. Mid-Labman (processing-slot) tasks only release "
            "locks on OK; other tasks may ask you to remove physical samples first."
        )
        for i, task_entry in enumerate(tasks_to_cancel):
            task_id = task_entry["task_id"]
            task_class = task_entry["type"]
            task_name = task_class.__name__

            lab_view = LabView(task_id=task_id)
            if lab_view.occupies_only_labman_processing():
                cli_logger.info(
                    f"({i + 1}/{n}) arming soft restart cleanup for mid-Labman task "
                    f"{task_name} ({task_id}); locks release on OK without clearing positions."
                )
                request_id = lab_view.arm_restart_cleanup(clear_positions=False)
            else:
                cli_logger.info(
                    f"({i + 1}/{n}) arming restart cleanup for task {task_name} "
                    f"({task_id}); acknowledge on the dashboard to release locks."
                )
                request_id = lab_view.arm_restart_cleanup(clear_positions=True)
            cli_logger.info(
                f"Restart cleanup request {request_id} posted for {task_name} ({task_id})."
            )

        cli_logger.info(
            "Restart cleanup prompts armed. Starting workers without waiting on OK."
        )

    def submit_ready_tasks(self):
        """
        Checking if there are any tasks that are ready to be submitted. (STATUS = READY)
        If so, submit them to task actor (dramatiq worker).
        """
        from alab_management.task_actor import run_task

        ready_task_entries = self.task_view.get_ready_tasks()
        for task_entry in ready_task_entries:
            self.logger.system_log(
                level="DEBUG",
                log_data={
                    "logged_by": self.__class__.__name__,
                    "type": "SendingTaskToActor",
                    "task_id": task_entry["task_id"],
                },
            )
            self.task_view.update_status(
                task_id=task_entry["task_id"], status=TaskStatus.INITIATED
            )
            self.task_view.set_message(
                task_id=task_entry["task_id"],
                message=WORKER_QUEUE_MESSAGE,
            )
            result = run_task.send_with_options(
                kwargs={"task_id_str": str(task_entry["task_id"])}
            )
            message_id = result.message_id
            cli_logger.info(
                f"Task {task_entry['type']} ({task_entry['task_id']}) sent to actor with message_id {message_id}. "
                f"A message from Task Actor will be logged with this task_id in alabos launch_worker. If not, "
                f"there can be an issue with the Dramatiq worker!"
            )
            self.task_view.set_task_actor_id(
                task_id=task_entry["task_id"], message_id=message_id
            )

    def handle_tasks_to_be_canceled(self):
        """Check if there are any tasks needs to be stopped."""
        tasks_to_be_cancelled = self.task_view.get_tasks_to_be_canceled(
            CancelingProgress.PENDING
        )

        for task_entry in tasks_to_be_cancelled:
            self.logger.system_log(
                level="DEBUG",
                log_data={
                    "logged_by": self.__class__.__name__,
                    "type": "CancellingTask",
                    "task_id": task_entry["task_id"],
                    "task_actor_id": task_entry.get("task_actor_id", None),
                },
            )
            if (
                message_id := task_entry.get("task_actor_id", None)
            ) is not None and abort_requested(message_id=message_id) is None:
                abort(message_id=message_id)
                cli_logger.info(
                    f"Task {task_entry['type']} ({task_entry['task_id']}) is being cancelled. "
                    f"Task Actor message_id: {message_id}"
                )
                self.task_view.update_canceling_progress(
                    task_id=task_entry["task_id"],
                    canceling_progress=CancelingProgress.WORKER_NOTIFIED,
                    original_progress=CancelingProgress[
                        task_entry["canceling_progress"]
                    ],
                )
