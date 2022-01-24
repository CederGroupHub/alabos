"""
Launch Dramatiq worker to submit tasks
"""


def launch_worker(args):
    from dramatiq.cli import main as launch
    from dramatiq.cli import make_argument_parser

    args = make_argument_parser().parse_args(args=["alab_management.task_actor"] + args)
    launch(args=args)
    return True
