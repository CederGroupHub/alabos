"""
Useful CLI tools for the alab_management package.
"""

import click

from .cleanup_lab import cleanup_lab
from .init_project import init_project
from .launch_lab import launch_dashboard, launch_lab
from .launch_worker import launch_worker
from .setup_lab import setup_lab
from .. import __version__

CONTEXT_SETTINGS = dict(help_option_names=["-h", "--help"])


@click.group("cli", context_settings=CONTEXT_SETTINGS)
def cli():
    """Managing workflow in Alab"""
    click.echo(
        rf"""       _    _       _         ___  ____
      / \  | | __ _| |__     / _ \/ ___| 
     / _ \ | |/ _` | '_ \   | | | \___ \ 
    / ___ \| | (_| | |_) |  | |_| |___) |
   /_/   \_\_|\__,_|_.__/    \___/|____/      

----  Alab OS v{__version__} -- Alab Project Team  ----
    """
    )


@cli.command("init", short_help="Init definition folder with default configuration")
def init_cli():
    if init_project():
        click.echo("Done")
    else:
        click.echo("Stopped")


@cli.command("setup", short_help="Read and write definitions to database")
def setup_lab_cli():
    if setup_lab():
        click.echo("Done")
    else:
        click.echo("Stopped")


@cli.command("launch", short_help="Start to run the lab")
@click.option(
    "--host",
    default="127.0.0.1",
)
@click.option("-p", "--port", default="8895", type=int)
@click.option("--debug", default=False, is_flag=True)
def launch_lab_cli(host, port, debug):
    click.echo(f"The dashboard will be served on http://{host}:{port}")
    launch_lab(host, port, debug)


@cli.command(
    "launch_worker",
    short_help="Launch Dramatiq worker in current folder",
    context_settings=dict(
        ignore_unknown_options=True,
        allow_extra_args=True,
        help_option_names=[],
    ),
)
@click.pass_context
def launch_worker_cli(ctx):
    launch_worker(ctx.args)


@cli.command("clean", short_help="Clean up the database")
@click.option("-a", "--all-collections", is_flag=True, default=False)
def cleanup_lab_cli(all_collections: bool):
    if cleanup_lab(all_collections):
        click.echo("Done")
    else:
        click.echo("Stopped")


@cli.command("launch_dashboard", short_help="Launch the dashboard alone.")
@click.option(
    "--host",
    default="127.0.0.1",
)
@click.option("-p", "--port", default="8895", type=int)
@click.option("--debug", default=False, is_flag=True)
def launch_dashboard_cli(host, port, debug):
    launch_dashboard(host, port, debug)
