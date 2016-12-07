import click
from nacl import signing
from nacl.encoding import URLSafeBase64Encoder

from .main import main
from ..sera import get_client
from ..utils import set_env_key, keygen


@main.group("create")
def create():
    """Create and update access, keypair, signature"""
    pass


@create.command()
@click.pass_context
def signature(ctx):
    """Create a signature to validate watchers"""
    if ctx.parent.parent.params['watcher']:
        click.echo("This command runs locally")
        raise click.Abort
    # Generate a new random signing key
    signing_key = signing.SigningKey.generate()
    signing_key_b64 = signing_key.encode(encoder=URLSafeBase64Encoder)
    verify_key = signing_key.verify_key
    verify_key_b64 = verify_key.encode(encoder=URLSafeBase64Encoder)
    set_env_key(ctx.obj['env_path'], 'SERA_SIGNATURE', signing_key_b64.decode())
    set_env_key(ctx.obj['env_path'], 'SERA_VERIFY_KEY', verify_key_b64.decode())
    if ctx.obj['verbosity']:
        click.echo('SERA_SIGNATURE and SERA_VERIFY_KEY written to %s' % ctx.obj['env_path'])


@create.command()
@click.pass_context
def keypair(ctx):
    """Create a public and private keypair with NaCL crypto"""
    ascii_pk = keygen(ctx.obj['env_path'])[0]
    if ctx.obj['verbosity']:
        click.echo('SERA_CLIENT_PUBLIC_KEY: %s' % ascii_pk)
        click.echo('SERA_CLIENT_PRIVATE_KEY: %s=' % ('*'*43))
        click.echo('Written to %s ' % str(ctx.obj['env_path']))


@create.command()
@click.pass_context
def access(ctx):
    """
    Creates access key(s) for a watcher to receive and send messages on any
    message queue it knows.

    Provider specific implementations may also create supporting Users, Groups,
    and Policy as necessary to limit the keypair's access.

    Requires appropriate permissions on the region.
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
