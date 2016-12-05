import logging
from collections import namedtuple

import click

from .main import main

from ..sera import remote
from ..utils import set_env_key

logger = logging.getLogger(__name__)


@main.command()
@click.pass_context
def set(ctx, expression):
    """set VARIABLE=VALUE"""
    if ctx.obj['local']:
        variable, value = expression.split('=')
        set_env_key(ctx.obj['env_path'], variable, value)
        cmd = namedtuple('cmd', ['subcommand', 'params'])
        return cmd('exit', {'message': 'set %s; exiting.' % variable})
    else:
        remote('set', ctx)
