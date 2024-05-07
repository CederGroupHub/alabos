"""
TaskLauncher is the core module of the system,
which actually executes the tasks.
"""

import time

from dramatiq_abort import abort, abort_requested

from alab_management.lab_view import LabView
from alab_management.logger import DBLogger
from alab_management.task_view import TaskView
from alab_management.task_view.task_enums import CancelingProgress, TaskStatus
from alab_management.utils.module_ops import load_definition


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
        super().__init__()
        time.sleep(1)  # allow some time for other modules to launch

    def run(self):
        """Start the loop."""
        while True:
            self._loop()
            # time.sleep(1)

    def _loop(self):
        self.handle_tasks_to_be_canceled()
        self.submit_ready_tasks()

    def clean_up_tasks_from_previous_runs(self):
        """Cleans up incomplete tasks that exist from the last time the taskmanager was running. Note that this will
        block the task queue until all samples in these tasks have been removed from the physical lab (confirmed via
        user requests on the dashboard).

        This typically occurs if the taskmanager was exited using SIGTERM (ctrl-c), in which case some tasks may
        still be in the RUNNING or CANCELLING state. These will be set to CANCELLED now.
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
            print("No dangling tasks found from previous alabos workers. Nice!")
            return

        print(
            f"""
              Found {len(tasks_to_cancel)} dangling tasks leftover from previous alabos workers. These tasks were in
              an unknown state (RUNNING or CANCELLING) when the alabos workers were stopped.

              We will now cancel them and remove their physical components from the lab. We will go through each task
              one by one. A user request will appear on the alabos dashboard for each task. Please acknowledge each
              request to remove the samples from the lab. Once all tasks have been addressed, the alabos workers will
              begin to process new tasks. Lets begin:"""
        )
        for i, task_entry in enumerate(tasks_to_cancel):
            task_id = task_entry["task_id"]
            task_class = task_entry["type"]
            task_name = task_class.__name__

            print(
                f"\n({i + 1}/{len(tasks_to_cancel)}) please clean up task {task_name} ({task_id}) using the ALabOS "
                f"dashboard..."
            )

            # puts a user request on the dashboard to remove all samples in this task from the physical lab,
            # blocks until request is acknowledged. There may be a duplicate request on the dashboard if the task was
            # already cancelled before the taskmanager was restarted. Acknowledging both should be fine.
            LabView(task_id=task_id).request_cleanup()

            # mark task as successfully cancelled
            self.task_view.update_status(task_id=task_id, status=TaskStatus.CANCELLED)
            print("\t Task cancelled successfully.")

        print("Cleanup is done, nice job. Lets get back to work!")

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
            result = run_task.send_with_options(
                kwargs={"task_id_str": str(task_entry["task_id"])}
            )
            message_id = result.message_id
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
                self.task_view.update_canceling_progress(
                    task_id=task_entry["task_id"],
                    canceling_progress=CancelingProgress.WORKER_NOTIFIED,
                    original_progress=CancelingProgress[task_entry["canceling_progress"]],
                )
