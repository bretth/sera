import click

from .main import main, lprint
from ..sera import run, remote


@main.command(
    context_settings=dict(
        ignore_unknown_options=True))
@click.pass_context
@click.argument('args', nargs=-1, type=click.UNPROCESSED)
def echo(ctx, args):
    """Test connection with [WATCHER]"""
    if ctx.obj['local']:
        out = run('echo', args)
    else:
        out = remote('echo', ctx)

    return lprint(ctx, out)
