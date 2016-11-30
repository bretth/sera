# -*- coding: utf-8 -*-
import logging
from os import getenv
import shutil
from socket import gethostname
import time

import click
import requests

from .sera import get_client, Host, run, remote
from .settings import service_template, RESET_TIME
from .utils import keygen as _keygen
from .utils import (
    get_ip_address,
    get_watcher_key, set_env_key, get_default_user,
    get_allowed_clients, configure_path, loadenv, configure_logging)


def mprint(ctx, out):
    """ echo output of stdout and stderr if it's not a watch invoked command """
    if out.stdout:
        click.echo(out.stdout)
    if out.stderr:
        click.echo(out.stderr)
    return out


@click.group()
@click.option('--timeout', '-t', type=int, default=-1)
@click.option('--debug', '-d', is_flag=True)
@click.option('--verbosity', '-v', type=int, default=1)
@click.option('--watcher', '-w')
@click.option('--local', '-l', is_flag=True)
@click.pass_context
def main(ctx, timeout, debug, verbosity, watcher, local):
    """
    With OPTIONS send COMMAND with ARGS to target WATCHER

    \b
    Examples:
    sera -w host.name echo hello world
    sera -w host.name echo -n hello world  # pass defined args
    sera -w host.name echo -- -n hello world  # pass arbitrary args
    sera . echo hello world  # substitute env $SERA_DEFAULT_WATCHER as target
    """

    # set some globals
    configure_logging(debug)
    sera_path = configure_path()
    env_path, env_path_exists = loadenv(sera_path)

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

    if not getenv('SERA_CLIENT_PRIVATE_KEY') and ctx.invoked_subcommand != 'keygen':
        raise click.ClickException(
            "No env SERA_CLIENT_PRIVATE_KEY. "
            "Maybe run `sera keygen` first.")

    if verbosity > 1 and getenv('SERA_REGION'):
        click.echo('Using region %s' % getenv('SERA_REGION'))
    namespace = getenv('SERA_NAMESPACE', 'sera')
    if verbosity > 1 and namespace != 'sera':
        click.echo('Using namespace "%s"' % namespace)
    if ctx.invoked_subcommand in ['create_provider_keys', 'install', 'keygen', 'watch'] or local:
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
        logging.debug(watcher.name)
        watcher_key = master.exchange_keys(watcher.name)
        if watcher_key:
            set_env_key(ctx.obj['known_watchers'], watcher.name, watcher_key)
        else:
            raise click.ClickException(
                'No public key received from %s' % watcher.uid)
    ctx.obj['watcher_key'] = watcher_key


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

    return mprint(ctx, out)


@main.command()
@click.pass_context
@click.option('--delay', '-d', type=int, default=0)
@click.argument('from_ip', required=False)
def disallow(ctx, delay, from_ip):
    """Delete previously allowed connection from ip address"""

    verbosity = ctx.obj.get('verbosity')
    if not from_ip:
        ctx.params['from_ip'] = from_ip = requests.get(
            'http://ipinfo.io').json().get('ip')
    if verbosity:
        click.echo('disallow from_ip %s' % from_ip)
    args = ['delete', 'allow', 'from', from_ip]
    if ctx.obj['local']:
        time.sleep(delay)
        out = run('ufw', args)
    else:
        out = remote('disallow', ctx)
    return mprint(ctx, out)


@main.command()
@click.pass_context
@click.argument('from_ip', required=False)
def allow(ctx, from_ip):
    """Open firewall connection from ip address"""

    verbosity = ctx.obj.get('verbosity')
    if not from_ip:
        ctx.params['from_ip'] = from_ip = requests.get(
            'http://ipinfo.io').json().get('ip')
    if verbosity:
        click.echo('allow from_ip %s' % from_ip)
    args = ['allow', 'from', from_ip]
    if ctx.obj['local']:

        out = run('ufw', args)
        if not out.returncode:
            ip_addr = get_ip_address(from_ip)
            out.subcommand = disallow
            out.params = {'delay': RESET_TIME, 'from_ip': from_ip}
            out.stdout += 'Resetting firewall on %s in %s seconds' % str(ip_addr, RESET_TIME)
    else:
        out = remote('allow', ctx)
    return mprint(ctx, out)


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


@main.command()
@click.pass_context
@click.option('--client', '-c', help="Allowed client public key")
def watch(ctx, client):
    """Watch for requests on current hostname or <name>"""
    verbosity = ctx.obj.get('verbosity')
    ctx.obj['host'] = name = ctx.parent.params['watcher'] or \
        getenv('SERA_DEFAULT_WATCHER', '') or gethostname()
    allowed_clients = get_allowed_clients(ctx.obj['known_clients'], client)
    timeout = ctx.obj['timeout']
    ctx.obj['local'] = True
    click.echo('Watching %s' % name)

    # wait for the host queue to be created by the client
    host = None
    delay = 0
    max_delay = int(getenv('SERA_MAX_DELAY', '20'))
    while not host:
        host = Host.get(name)
        time.sleep(delay)
        if delay < max_delay:
            delay += 1

    start = time.time()
    while True:
        cmd = host.receive(timeout=timeout)
        if cmd and cmd.public_key not in allowed_clients:
            if verbosity:
                click.echo("Client public key '%s' not allowed" %
                           str(cmd.public_key))
                click.echo("Ignoring command '%s'" % str(cmd.name))
        elif cmd and cmd.name == 'public_key':
            if verbosity:
                click.echo('Sending public key to %s' % cmd.host)
            host.send(cmd.host, 'public_key %s' % getenv(
                'SERA_CLIENT_PUBLIC_KEY'), await_response=False)
        elif cmd and cmd.public_key in allowed_clients and cmd.name:
            if verbosity:
                click.echo('Received cmd %s' % str(cmd.name))
            subcommand = main.get_command(ctx, cmd.name)
            params = cmd.params
            while subcommand:
                out = ctx.invoke(subcommand, **params)
                host.send(
                    cmd.host,
                    cmd.name,
                    params=cmd.params,
                    stdout=out.stdout,
                    stderr=out.stderr,
                    returncode=out.returncode,
                    recipient_key=cmd.public_key,
                    await_response=False)
                subcommand = getattr(out, 'subcommand', None)
                params = getattr(out, 'params', None)

        duration = time.time() - start
        if timeout > -1 and duration > timeout:
            return


@main.group('install')
@click.pass_context
def install(ctx):
    """install client_key|access_key|secret_key|region [key]"""


@install.command()
@click.pass_context
@click.option('--path', '-p', help="Path to installed file")
def service(ctx, path):
    """Install systemd service"""
    path = path or '/etc/systemd/system/sera.service'
    if ctx.obj['verbosity']:
        click.echo('Installing service at %s' % path)
    output = service_template.substitute(
        executable=shutil.which('sera'),
        user='root')  # todo allow sudo
    with open(path, 'w') as file:
        file.write(output)


@install.command()
@click.pass_context
@click.argument('client_key')
def client(ctx, client_key):
    """Install client_key in known_clients"""
    clients = get_allowed_clients(ctx.obj['known_clients'])
    if client_key not in clients:
        with ctx.obj['known_clients'].open(mode='w+') as file:
            file.writelines([client_key])


@install.command()
@click.pass_context
@click.argument('access_key')
def access(ctx, access_key):
    """Install provider SERA_ACCESS_KEY in env"""
    set_env_key(ctx.obj['env_path'], 'SERA_ACCESS_KEY', access_key)


@install.command()
@click.pass_context
@click.argument('secret_key')
def secret(ctx, secret_key):
    """Install provider SERA_SECRET_KEY in env"""
    set_env_key(ctx.obj['env_path'], 'SERA_SECRET_KEY', secret_key)


@install.command()
@click.pass_context
@click.argument('region')
def region(ctx, region):
    """Install provider SERA_REGION in env"""
    set_env_key(ctx.obj['env_path'], 'SERA_REGION', region)
