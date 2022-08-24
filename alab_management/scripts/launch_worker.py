"""
Launch Dramatiq worker to submit tasks
"""


def launch_worker(args):
    from dramatiq.cli import main as launch
    from dramatiq.cli import make_argument_parser
    from argparse import Namespace

    args = make_argument_parser().parse_args(
        args=["alab_management.task_actor"] + args,
        namespace=Namespace(processes=4, threads=128),
    )
    launch(args=args)
    return True
