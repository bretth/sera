from base64 import urlsafe_b64encode
from collections import OrderedDict
from os import getenv
from pathlib import Path


from dotenv.main import set_key, parse_dotenv
from nacl.public import PrivateKey, PublicKey, Box
from nacl.encoding import URLSafeBase64Encoder
from nacl.utils import random


def get_default_envpath(env=None):
    if not env:
        env = Path.home() / '.env'
        if env.exists():
            return str(env)
        else:
            return None


def get_watcher_key(name, path=None):
    if not path:
        path = Path.home() / '.sera_known_watchers'
    if not path.exists():
        path.touch(mode=0o644)
        return
    dotenv_as_dict = OrderedDict(parse_dotenv(str(path)))
    return dotenv_as_dict.get(name)


def set_watcher_key(name, watcher_key, path=None):
    if not path:
        path = Path.home() / '.sera_known_watchers'
    if not path.exists():
        path.touch(mode=0o644)
    return set_key(str(path), name, watcher_key, quote_mode="auto")[0]


def keygen(env='', write=False):
    if write:
        if not env:
            dotenv = Path.cwd() / '.env'
        else:
            dotenv = Path(env)

        if not dotenv.exists():
            dotenv.touch(mode=0o700)

    private_key = PrivateKey.generate()
    public_key = private_key.public_key
    ascii_sk = urlsafe_b64encode(bytes(private_key)).decode('ascii')
    ascii_pk = urlsafe_b64encode(bytes(public_key)).decode('ascii')

    if write:
        set_key(
            str(dotenv),
            'SERA_PRIVATE_KEY',
            ascii_sk,
            'auto')

        set_key(
            str(dotenv),
            'SERA_PUBLIC_KEY',
            ascii_pk,
            'auto')

    return ascii_pk, ascii_sk


def encrypt(msg, recipient_key, private_key='', encoding='utf-8'):
    """Encrypt a message with the given recipient public key"""

    private_key = private_key or getenv('SERA_PRIVATE_KEY')
    skey = PrivateKey(private_key, URLSafeBase64Encoder)
    rkey = PublicKey(recipient_key, URLSafeBase64Encoder)
    msg = bytes(msg, encoding)
    box = Box(skey, rkey)
    nonce = random(Box.NONCE_SIZE)
    return box.encrypt(msg, nonce)


def decrypt(msg, sender_key, private_key='', encoding='utf-8'):
    """Decrypt a message with the given private key or SERA_PRIVATE_KEY"""
    private_key = private_key or getenv('SERA_PRIVATE_KEY')
    skey = PrivateKey(private_key, URLSafeBase64Encoder)
    pkey = PublicKey(sender_key, URLSafeBase64Encoder)
    box = Box(skey, pkey)
    return box.decrypt(msg).decode('utf-8')




