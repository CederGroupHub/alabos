"""Useful CLI tools for the alab_management package."""
import click

from alab_management import __version__
from alab_management.config import AlabConfig

from .cleanup_lab import cleanup_lab
from .init_project import init_project
from .launch_lab import launch_dashboard, launch_lab
from .launch_worker import launch_worker
from .setup_lab import setup_lab

CONTEXT_SETTINGS = {"help_option_names": ["-h", "--help"]}


@click.group("cli", context_settings=CONTEXT_SETTINGS)
def cli():
    """Managing workflow in Alab."""
    click.echo(
        rf"""       _    _       _         ___  ____
      / \  | | __ _| |__     / _ \/ ___|
     / _ \ | |/ _` | '_ \   | | | \___ \
    / ___ \| | (_| | |_) |  | |_| |___) |
   /_/   \_\_|\__,_|_.__/    \___/|____/

----  Alab OS v{__version__} -- Alab Project Team  ----
    Simulation mode: {"ON" if AlabConfig().is_sim_mode() else "OFF"}
    """
    )


@cli.command("init", short_help="Init definition folder with default configuration")
def init_cli():
    """Init definition folder with default configuration."""
    if init_project():
        click.echo("Done")
    else:
        click.echo("Stopped")


@cli.command("setup", short_help="Read and write definitions to database")
def setup_lab_cli():
    """Read and write definitions to database."""
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
    """Start to run the lab."""
    click.echo(f"The dashboard will be served on http://{host}:{port}")
    launch_lab(host, port, debug)


@cli.command(
    "launch_worker",
    short_help="Launch Dramatiq worker in current folder",
    context_settings={
        "ignore_unknown_options": True,
        "allow_extra_args": True,
        "help_option_names": [],
    },
)
@click.pass_context
def launch_worker_cli(ctx):
    """Launch Dramatiq worker in current folder."""
    launch_worker(ctx.args)


@cli.command("clean", short_help="Clean up the database")
@click.option("-a", "--all-collections", is_flag=True, default=False)
def cleanup_lab_cli(all_collections: bool):
    """Clean up the database."""
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
    """Launch the dashboard alone."""
    launch_dashboard(host, port, debug)


@cli.command(
    "copy_completed_experiments",
    short_help='Copy completed experiments from working database to completed database. Note that "mongodb_completed" '
    "must be specified in the config file.",
)
def copy_completed_experiments_cli():
    """Copy completed experiments from working database to completed database. Note that "mongodb_completed" must be
    specified in the config file.
    """
    from alab_management.experiment_view import CompletedExperimentView

    CompletedExperimentView().save_all()


@cli.command(
    "launch_summary_dashboard",
    short_help="Launch the summary dashboard, which provides statistics on the state of the lab and its tasks.",
)
@click.option(
    "--host",
    default="0.0.0.0",
)
@click.option("-p", "--port", default="8900", type=int)
def launch_summary_dashboard(host, port):
    """Launch the summary dashboard, which provides statistics on the state of the lab and its tasks."""
    from alab_management.dashboard.plotly import launch

    launch(host=host, port=port)
