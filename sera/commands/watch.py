import time
from os import getenv
from socket import gethostname

import click

from .main import main
from ..sera import Host
from ..utils import get_allowed_clients


@main.command()
@click.pass_context
@click.option('--client', '-c', help="Allowed client public key")
def watch(ctx, client):
    """Receive remote commands"""
    verbosity = ctx.obj.get('verbosity')
    ctx.obj['host'] = name = ctx.parent.params['watcher'] or gethostname()
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

    # host queue created - await a command
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
            while subcommand:  # can chain commands
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
