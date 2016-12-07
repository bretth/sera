from hashlib import sha256
from pathlib import Path

import click
from nacl.exceptions import CryptoError
from nacl.utils import random
from nacl.secret import SecretBox
from nacl.encoding import Base64Encoder

from .main import main, lprint
from ..sera import remote


def apply_crypto(password, recursive, root, pattern, command='encrypt'):
    box = SecretBox(sha256(password).digest())

    if recursive:
        files = Path(root).rglob(pattern)
    else:
        files = Path(root).glob(pattern)
    files = [file for file in files if file.is_file()]
    error = None
    err_count = 0
    total_count = len(files)
    for file in files:
        content = file.read_bytes()
        try:
            if command == 'encrypt':
                nonce = random(SecretBox.NONCE_SIZE)
                output = box.encrypt(content, nonce, Base64Encoder)
                outfile = file.name + '.nacl'
            else:
                outfile = file.name[:-5]
                output = box.decrypt(content, encoder=Base64Encoder)
            click.echo(str(file))
        except CryptoError as err:
            error = str(err)
            err_count += 1
            click.echo('Failed to %s %s' % (command, str(file)))
            continue
        parent = file.parent
        outfile_path = parent / outfile
        outfile_path.write_bytes(output)
    if error:
        if err_count == total_count:
            msg = 'Error'
        else:
            msg = 'Warning'
        click.echo(
            '%s: %s on %i out of %i files' %
            (msg, error, err_count, total_count), err=True)


@main.command()
@click.pass_context
@click.option('--recursive', '-R', is_flag=True)
@click.option('--password', '-p')
@click.argument("root")
@click.argument("pattern")
def encrypt(ctx, recursive, password, root, pattern):
    """Encrypt files on path matching glob pattern"""
    password = password or click.prompt("Enter password", hide_input=True).strip().encode()
    if ctx.obj['local']:
        apply_crypto(password, recursive, root, pattern)
    else:
        out = remote('encrypt', ctx)
        return lprint(ctx, out)


@main.command()
@click.pass_context
@click.option('--recursive', '-R', is_flag=True)
@click.option('--password', '-p')
@click.argument("root")
def decrypt(ctx, recursive, password, root):
    """Decrypt .nacl files on a path and overwrite existing"""
    password = password or click.prompt("Enter password", hide_input=True).strip().encode()
    if ctx.obj['local']:
        apply_crypto(password, recursive, root, pattern='*.nacl', command='decrypt')
    else:
        out = remote('decrypt', ctx)
        return lprint(ctx, out)
