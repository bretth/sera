# -*- coding: utf-8 -*-
import logging
from os import getenv
from socket import gethostname
import time

import click
import requests
from dotenv import load_dotenv

from .sera import get_client, Host, run, remote
from .settings import service_template
from .utils import keygen as _keygen
from .utils import get_watcher_key, set_watcher_key, get_default_envpath, get_allowed_clients

logger = logging.getLogger(__name__)


def mprint(ctx, out):
    """ echo output of stdout and stderr if it's not a watch invoked command """
    if out.stdout:
        click.echo(out.stdout)
    if out.stderr:
        click.echo(out.stderr)
    return out


@click.group()
@click.option(
    '--env', '-e',
    type=click.Path(exists=True, dir_okay=False, resolve_path=True),
    help='Path to environment variables file')
@click.option('--timeout', '-t', type=int, default=-1)
@click.option(
    '--known', '-k',
    type=click.Path(exists=True, dir_okay=False, resolve_path=True),
    help='Path to known watchers file')
@click.option('--debug', '-d', is_flag=True)
@click.option('--verbose', '-v', is_flag=True)
@click.option('--watcher', '-w')
@click.option('--local', '-l', is_flag=True)
@click.pass_context
def main(ctx, env, timeout, known, debug, verbose, watcher, local):
    """
    With OPTIONS send COMMAND with ARGS to target WATCHER

    \b
    Examples:
    sera host.name echo hello world
    sera host.name echo -n hello world  # pass defined args
    sera host.name echo -- -n hello world  # pass arbitrary args
    sera . echo hello world  # substitute env $SERA_DEFAULT_WATCHER as target
    """
    if debug:
        logger = logging.getLogger('sera')
        logger.setLevel(logging.DEBUG)
        formatter = logging.Formatter('[%(levelname)s] %(name)s:%(message)s')
        handler = logging.StreamHandler()
        handler.setFormatter(formatter)
        logger.addHandler(handler)
    # set some globals
    ctx.obj = {'local': local, 'timeout': timeout, 'verbose': verbose}
    envpath = get_default_envpath(env)
    if not envpath and verbose:
        click.echo('Using provider credentials (if defined)')
    else:
        if verbose:
            click.echo('Loading %s' % envpath)
        load_dotenv(envpath)
    if not getenv('SERA_PRIVATE_KEY'):
        click.echo('Generating encryption keypair')
        public_key = _keygen(env, write=True)[0]
    else:
        public_key = getenv('SERA_PUBLIC_KEY')

    if verbose and getenv('SERA_REGION'):
        click.echo('Using region %s' % getenv('SERA_REGION'))
    namespace = getenv('SERA_NAMESPACE', 'Sera')
    if verbose and namespace != 'Sera':
        click.echo('Using namespace "%s"' % namespace)
    if ctx.invoked_subcommand in ['watch', 'create_provider_keys'] or local:
        return

    # master related logic
    if not watcher:
        watcher = getenv('SERA_DEFAULT_WATCHER', '')
    watcher = Host.get(watcher, create=True)
    # use the masters public key as its name
    master = Host.get(public_key.replace('=', ''), create=True)
    ctx.obj['master'] = master
    ctx.obj['watcher'] = watcher
    known_path = known or getenv('SERA_KNOWN_WATCHERS')
    watcher_key = get_watcher_key(watcher.name, known_path)
    if not watcher_key:
        click.echo('Exchanging public keys with %s' % watcher.uid)
        logging.debug(watcher.name)
        watcher_key = master.exchange_keys(watcher.name)
        if watcher_key:
            set_watcher_key(watcher.name, watcher_key, known_path)
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
@click.argument('from_ip', required=False)
def allow(ctx, from_ip):
    """Open firewall connection from ip address"""

    verbose = ctx.obj.get('verbose')
    if not from_ip:
        ctx.params['from_ip'] = from_ip = requests.get(
            'http://ipinfo.io').json().get('ip')
    if verbose:
        click.echo('allow from_ip %s' % from_ip)
    args = ['allow', 'from', from_ip]
    if ctx.obj['local']:
        out = run('ufw', args)
    else:
        out = remote('allow', ctx)
        mprint(ctx, out)
        if click.confirm('Enter to disallow', default=True):
            return ctx.invoke(disallow)
    return mprint(ctx, out)


@main.command()
@click.pass_context
@click.option('--delay', '-d', type=int, default=0)
@click.argument('from_ip', required=False)
def disallow(ctx, delay, from_ip):
    """Delete previously allowed connection from ip address"""

    verbose = ctx.obj.get('verbose')
    if not from_ip:
        ctx.params['from_ip'] = from_ip = requests.get(
            'http://ipinfo.io').json().get('ip')
    if verbose:
        click.echo('disallow from_ip %s' % from_ip)
    args = ['delete', 'allow', 'from', from_ip]
    if ctx.obj['local']:
        time.sleep(delay)
        out = run('ufw', args)
    else:
        out = remote('disallow', ctx)
    return mprint(ctx, out)


@main.command()
def keygen():
    """Create a public and private keypair with NaCL crypto"""
    ascii_pk, ascii_sk = _keygen()
    click.echo('SERA_PUBLIC_KEY: %s' % ascii_pk)
    click.echo('SERA_PRIVATE_KEY: %s' % ascii_sk)


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
@click.option('--client', '-c', help="Allowed client")
def watch(ctx, client):
    """Watch for requests on current hostname or <name>"""
    verbose = ctx.obj.get('verbose')
    ctx.obj['host'] = name = ctx.parent.params['watcher'] or \
        getenv('SERA_DEFAULT_WATCHER', '') or gethostname()
    allowed_clients = get_allowed_clients(client)
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
            if verbose:
                click.echo("Client public key '%s' not allowed" %
                           str(cmd.public_key))
                click.echo("Ignoring command '%s'" % str(cmd.name))
        elif cmd and cmd.name == 'public_key':
            if verbose:
                click.echo('Sending public key to %s' % cmd.host)
            host.send(cmd.host, 'public_key %s' % getenv(
                'SERA_PUBLIC_KEY'), await_response=False)
        elif cmd and cmd.public_key in allowed_clients and cmd.name:
            if verbose:
                click.echo('Received cmd %s' % str(cmd.name))
            subcommand = main.get_command(ctx, cmd.name)
            out = ctx.invoke(subcommand, **cmd.params)
            host.send(
                cmd.host,
                cmd.name,
                params=cmd.params,
                stdout=out.stdout,
                stderr=out.stderr,
                returncode=out.returncode,
                recipient_key=cmd.public_key,
                await_response=False)
        duration = time.time() - start
        if timeout > -1 and duration > timeout:
            return


@main.group('install')
@click.pass_context
def install(ctx):
    """install [service|key] [client_key]"""


@install.command()
@click.pass_context
@click.option('--path', '-p', help="Path to installed file")
def service(ctx, path):
    """Install systemd service"""
    path = path or '/etc/systemd/system/sera.service'
    if ctx.obj['verbose']:
        click.echo('Installing service at %s' % path)
        output = service_template.substitute(executable=shutil.which('sera'))
        with open(path, 'w') as file:
            file.write(output)

