import click

from .cleanup_lab import cleanup_lab
from .launch_lab import launch_lab
from .setup_lab import setup_lab
from .. import __version__

CONTEXT_SETTINGS = dict(help_option_names=['-h', '--help'])


@click.group("cli", context_settings=CONTEXT_SETTINGS)
def cli():
    """Managing workflow in Alab"""
    click.echo(rf"""       _    _       _         ___  ____
      / \  | | __ _| |__     / _ \/ ___| 
     / _ \ | |/ _` | '_ \   | | | \___ \ 
    / ___ \| | (_| | |_) |  | |_| |___) |
   /_/   \_\_|\__,_|_.__/    \___/|____/      

----  Alab OS v{__version__} -- Alab Project Team  ----
    """)


@cli.command("clean", short_help="Clean up the database")
@click.option("-a", "--all-collections", is_flag=True, default=False)
def cleanup_lab_cli(all_collections: bool):
    if cleanup_lab(all_collections):
        click.echo("Done")


@cli.command("launch", short_help="Start to run the lab")
@click.option("--host", default="127.0.0.1", )
@click.option("-p", "--port", default="8895", type=int)
@click.option("--debug", default=False, is_flag=True)
def launch_lab_cli(host, port, debug):
    if launch_lab(host, port, debug):
        click.echo("Done")


@cli.command("setup", short_help="Read and write definitions to database")
def setup_lab_cli():
    setup_lab()
