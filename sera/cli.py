# -*- coding: utf-8 -*-
import click


from .commands.main import main

from .commands.echo import echo
from .commands.install import install
from .commands.addremove import add, remove
from .commands.allow import allow, disallow
from .commands.end import end
from .commands.export import export
from .commands.watch import watch

from .sera import get_client
from .utils import keygen as _keygen


@main.command()
@click.pass_context
def keygen(ctx):
    """Create a public and private keypair with NaCL crypto"""
    ascii_pk = _keygen(ctx.obj['env_path'])[0]
    if ctx.obj['verbosity']:
        click.echo('SERA_CLIENT_PUBLIC_KEY: %s' % ascii_pk)
        click.echo('SERA_CLIENT_PRIVATE_KEY: %s=' % ('*'*43))
        click.echo('Written to %s ' % str(ctx.obj['env_path']))


@main.command()
@click.pass_context
def create_provider_keys(ctx):
    """
    Creates a keypair for a watcher to receive and send messages on any message queue it knows.
    Provider specific implementations may also create supporting Users, Groups, and Policy as
    necessary to limit the keypair's access.

    Requires an access key and secret key with appropriate permissions on the region.
    """
    client = get_client()()
    access_key, secret_key = client.create_provider_keys()
    click.echo('%s keypair for watcher access:' % client.name)

    if access_key and secret_key:
        click.echo('[Warning: This will only be shown once]')
        click.echo('SERA_ACCESS_KEY=%s' % access_key)
        click.echo('SERA_SECRET_KEY=%s' % secret_key)
    else:
        click.echo('The keypair has been previously created')

