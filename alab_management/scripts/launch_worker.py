"""Launch Dramatiq worker to submit tasks."""

from alab_management.task_manager.task_manager import TaskManager


def launch_worker(args):
    """Launch a Dramatiq worker process to execute tasks."""
    from argparse import Namespace

    from dramatiq.cli import main as launch
    from dramatiq.cli import make_argument_parser

    args = make_argument_parser().parse_args(
        args=["alab_management.task_actor", *args],
        namespace=Namespace(processes=6, threads=128),
    )

    launch(args=args)

    return True
