"""Useful CLI tools for the alab_management package."""

import os

import click

from alab_management.__init__ import __version__

from .cleanup_lab import cleanup_lab
from .init_project import init_project
from .launch_lab import launch_dashboard, launch_lab
from .launch_worker import launch_worker
from .seed_demo_data import seed_demo_data
from .setup_lab import setup_lab

CONTEXT_SETTINGS = {"help_option_names": ["-h", "--help"]}

ALABOS_BANNER = rf"""       _    _       _         ___  ____
      / \  | | __ _| |__     / _ \/ ___|
     / _ \ | |/ _` | '_ \   | | | \___ \
    / ___ \| | (_| | |_) |  | |_| |___) |
   /_/   \_\_|\__,_|_.__/    \___/|____/

----  Alab OS v{__version__} -- Alab Project Team  ----
"""


def _should_print_cli_banner(ctx: click.Context) -> bool:
    if os.environ.get("ALABOS_QUIET_CLI", "").strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }:
        return False
    return ctx.invoked_subcommand != "launch_worker"


@click.group("cli", context_settings=CONTEXT_SETTINGS)
@click.pass_context
def cli(ctx):
    """Managing workflow in Alab."""
    if _should_print_cli_banner(ctx):
        click.echo(ALABOS_BANNER)


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
    from alab_management.utils.logger import configure_logging

    configure_logging()
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
    from alab_management.config import AlabOSConfig

    click.echo(f'Simulation mode: {"ON" if AlabOSConfig().is_sim_mode() else "OFF"}')
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
@click.option("-f", "--_force_i_know_its_dangerous", is_flag=True, default=False)
@click.option("--database_name")
def cleanup_lab_cli(
    all_collections: bool, _force_i_know_its_dangerous: bool, database_name: str
):
    """Clean up the database."""
    if cleanup_lab(
        all_collections, _force_i_know_its_dangerous, database_name=database_name
    ):
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


@cli.command(
    "seed_demo_data",
    short_help="Seed demo samples, tasks, and experiments into the working database for UI testing.",
)
@click.option(
    "--keep-existing-demo",
    is_flag=True,
    default=False,
    help="Do not replace previously seeded demo documents tagged by the demo seeder.",
)
def seed_demo_data_cli(keep_existing_demo: bool):
    """Seed demo data into the working database for dashboard testing."""
    summary = seed_demo_data(replace_existing=not keep_existing_demo)
    click.echo(
        "Seeded demo data: "
        f"{summary['samples_created']} samples, "
        f"{summary['tasks_created']} tasks, "
        f"{summary['experiments_created']} experiments."
    )
