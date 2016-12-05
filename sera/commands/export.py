import logging

import click

from .main import main
from ..sera import remote, RemoteCommand
from ..utils import set_env_key

logger = logging.getLogger(__name__)


@main.command()
@click.pass_context
@click.argument('expression')
def export(ctx, expression):
    """export VARIABLE=VALUE"""
    if ctx.obj['local']:
        variable, value = expression.split('=')
        set_env_key(ctx.obj['env_path'], variable, value)
        cp = RemoteCommand(
            returncode=0,
            subcommand='end',
            params={'message': 'exported %s; exiting...' % variable})
        return cp
    else:
        remote('export', ctx)
