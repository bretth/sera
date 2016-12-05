import logging
import sys

import click

from .main import main

logger = logging.getLogger(__name__)


@main.command()
@click.pass_context
def exit(ctx, message):
    logger.info(message)
    sys.exit()
