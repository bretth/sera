import logging
import sys

import click

from .main import main

logger = logging.getLogger(__name__)


@main.command()
@click.pass_context
@click.argument('message', default='')
def end(ctx, message):
    """
    Exits the program.

    Typically used as a subcommand to exit after a response has been sent to
    the client.

    """

    if ctx.obj['verbosity']:
        click.echo(message)
    sys.exit()
