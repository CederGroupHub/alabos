"""Launch Dramatiq worker to submit tasks."""
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

    launch(args=args)

    return True
