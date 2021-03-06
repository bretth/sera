import click

from .main import main
from ..sera import remote
from ..utils import get_allowed_clients


@main.command()
@click.pass_context
@click.argument('client_key')
def add(ctx, client_key):
    """add client public key to known clients"""
    if ctx.obj['local']:
        clients = get_allowed_clients(ctx.obj['known_clients'])
        if client_key not in clients:
            with ctx.obj['known_clients'].open(mode='w+') as file:
                file.writelines([client_key])
    else:
        remote('client', ctx)


@main.command()
@click.pass_context
def revoke(ctx, client_key):
    """remove client public key from known clients"""
    if ctx.obj['local']:
        clients = get_allowed_clients(ctx.obj['known_clients'])
        with ctx.obj['known_clients'].open(mode='w') as file:
            for existing_client_key in clients:
                if client_key != existing_client_key:
                    file.writelines([client_key])
    else:
        remote('revoke', ctx)