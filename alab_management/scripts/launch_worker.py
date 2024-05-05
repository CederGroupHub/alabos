"""Launch Dramatiq worker to submit tasks."""
import os

from alab_management.task_manager.task_manager import TaskManager


def launch_worker(args):
    """Launch a Dramatiq worker process to execute tasks."""
    from argparse import Namespace

    from dramatiq.cli import main as launch
    from dramatiq.cli import make_argument_parser

    # Clean up any leftover tasks from previous runs. This blocks new workers until cleanup is done!
    TaskManager().clean_up_tasks_from_previous_runs()  # pylint: disable=protected-access

    args = make_argument_parser().parse_args(
        args=["alab_management.task_actor", *args],
        namespace=Namespace(processes=6, threads=128),
    )

    lock_file = os.path.expanduser("~/.alabos_worker_lock")
    if os.path.exists(lock_file):
        raise RuntimeError("Worker lock file exists. Another worker is already running.")

    with open(lock_file, "w", encoding="utf-8") as f:
        f.write(str(os.getpid()))
    try:
        launch(args=args)
    finally:
        os.remove(lock_file)
    return True
