from pathlib import Path
from shutil import which
from subprocess import run, PIPE

import click

from .main import main, lprint


@main.command()
@click.pass_context
@click.argument('watcher')
def symlink(ctx, watcher):
    """Locally install a symlink to sera"""
    if ctx.parent.params['watcher']:
        click.echo("This command runs locally")
        raise click.Abort
    source = Path(which('sera'))
    target = source.parent / watcher

    if ctx.obj['verbosity']:
        click.echo('Installing symlink at %s' % str(target))
    out = run(
        ['ln', '-s', str(source), str(target)],
        stdout=PIPE,
        stderr=PIPE,
        universal_newlines=True)
    return lprint(ctx, out)