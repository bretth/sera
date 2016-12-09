# -*- coding: utf-8 -*-
from os import getenv
from sys import argv

import click

from ..sera import Host
from ..settings import DEFAULT_TIMEOUT
from ..utils import (
    get_default_watcher,
    get_watcher_key, set_env_key,
    configure_path, loadenv, configure_logging)


def get_default_timeout():
    if len(argv) > 1 and 'watch' in argv[1:]:
        return -1
    else:
        return int(getenv('SERA_TIMEOUT', DEFAULT_TIMEOUT))


def lprint(ctx, out):
    """ echo output of stdout and stderr if it's not a watch invoked command """
    if out.stdout:
        click.echo(out.stdout)
    if out.stderr:
        click.echo(out.stderr)
    return out


@click.group()
@click.option('--timeout', '-t', type=int, default=get_default_timeout)
@click.option('--debug', '-d', is_flag=True)
@click.option('--verbosity', '-v', type=int, default=1)
@click.option('--watcher', '-w', default=get_default_watcher)
@click.pass_context
def main(ctx, timeout, debug, verbosity, watcher):
    """
    With OPTIONS send COMMAND with ARGS to target WATCHER

    \b
    Examples:
    sera -w host.name echo hello world
    sera -w host.name echo -n hello world  # pass defined args
    sera -w host.name echo -- -n hello world  # pass arbitrary args
    """

    # set some globals
    configure_logging(debug)
    sera_path = configure_path()
    env_path, env_path_exists = loadenv(sera_path)
    local = True if not watcher else False

    ctx.obj = {
        'local': local,
        'timeout': timeout,
        'verbosity': verbosity,
        'known_clients': sera_path / 'known_clients',
        'known_watchers': sera_path / 'known_watchers',
        'env_path': env_path}
    if not env_path_exists and ctx.invoked_subcommand != 'keygen':
        if verbosity:
            click.echo('No env file. Using provider credentials (if defined)')

    if not getenv('SERA_CLIENT_PRIVATE_KEY') and ctx.invoked_subcommand != 'create':
        raise click.ClickException(
            "No env SERA_CLIENT_PRIVATE_KEY. "
            "Maybe run `sera create keypair` first.")

    if verbosity > 1 and getenv('SERA_REGION'):
        click.echo('Using region %s' % getenv('SERA_REGION'))
    namespace = getenv('SERA_NAMESPACE', 'sera')
    if verbosity > 1 and namespace != 'sera':
        click.echo('Using namespace "%s"' % namespace)
    if ctx.invoked_subcommand in ['create', 'install', 'watch'] or local:
        return

    # master related logic
    if not watcher:
        watcher = getenv('SERA_DEFAULT_WATCHER', '')
    watcher = Host.get(watcher, create=True)

    # use the masters public key as its name
    master = Host.get(getenv('SERA_CLIENT_PUBLIC_KEY').replace('=', ''), create=True)
    ctx.obj['master'] = master
    ctx.obj['watcher'] = watcher
    watcher_key = get_watcher_key(ctx.obj['known_watchers'], watcher.name)
    if not watcher_key:
        if verbosity:
            click.echo('Exchanging public keys with %s' % watcher.uid)
        watcher_key = master.exchange_keys(watcher.name)
        if watcher_key:
            set_env_key(ctx.obj['known_watchers'], watcher.name, watcher_key)
        else:
            raise click.ClickException(
                'No public key received from %s' % watcher.uid)
    ctx.obj['watcher_key'] = watcher_key

