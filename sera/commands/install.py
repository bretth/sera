import shutil

import click

from .main import main
from ..settings import service_template


@main.command()
@click.pass_context
@click.option('--path', '-p', help="Path to installed file")
def install(ctx, path):
    """Locally install systemd service"""
    if ctx.parent.params['watcher']:
        click.echo("This command runs locally")
        raise click.Abort
    path = path or '/etc/systemd/system/sera.service'
    if ctx.obj['verbosity']:
        click.echo('Installing service at %s' % path)
    output = service_template.substitute(
        executable=shutil.which('sera'),
        user='root')
    with open(path, 'w') as file:
        file.write(output)
