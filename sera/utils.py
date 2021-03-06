from base64 import urlsafe_b64encode
from collections import OrderedDict
from os import getenv, getuid
import logging
from pwd import getpwuid
from pathlib import Path
from shutil import chown
import socket
import sys


from dotenv.main import set_key, parse_dotenv
from dotenv import load_dotenv

from nacl.public import PrivateKey, PublicKey, Box
from nacl.encoding import URLSafeBase64Encoder
from nacl.utils import random

ALLOWED_CLIENTS = []


def get_default_watcher():
    watcher = Path(sys.argv[0]).name
    if watcher != 'sera':
        return watcher
    return ''


def get_ip_address(target_ip):
    soc = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    soc.connect((target_ip, 22))
    ip_addr = soc.getsockname()[0]
    soc.close()
    return ip_addr


def get_default_user():
    home = Path.home()
    current_user = getpwuid(getuid()).pw_name
    if current_user != 'root' and home.exists():
        return getpwuid(home.stat().st_uid).pw_name
    return 'root'


def configure_logging(debug):
    logger = logging.getLogger('sera')
    if debug:
        logger.setLevel(logging.DEBUG)
        formatter = logging.Formatter('[%(levelname)s] %(name)s:%(message)s')
        handler = logging.StreamHandler()
        handler.setFormatter(formatter)
        logger.addHandler(handler)
    return logger


def configure_path():
    """
    Precedence of configuration
    /etc/sera  (default)
    ~/.sera (preferred)

    """
    current_user = getpwuid(getuid()).pw_name
    home = Path.home()

    if current_user == 'root' or home.exists() is False:  # sudo, root or system user
        sera_path = Path('/etc', 'sera')
    else:
        sera_path = home / '.sera'

    if not sera_path.exists():
        if current_user == 'root' or sera_path == home / '.sera':
            sera_path.mkdir()

    return sera_path


def loadenv(base_path):
    """
    Precedence of env loading
    /etc/sera/env (default)
    ~/.sera/env (preferred)

    Existing environment variables are not overwritten.
    """
    envpath = base_path / 'env'
    default_env_path = Path('/etc') / 'sera' / 'env'
    if envpath.exists():
        load_dotenv(str(envpath))
        return envpath, True
    elif envpath != default_env_path and default_env_path.exists():
        load_dotenv(str(default_env_path))
        return default_env_path, True
    return envpath, False


def get_allowed_clients(path, client=None):
    global ALLOWED_CLIENTS
    if client:
        return [client]
    elif ALLOWED_CLIENTS:
        return ALLOWED_CLIENTS
    if path.exists():
        with path.open() as file:
            ALLOWED_CLIENTS = [line.rstrip('\n') for line in file.readlines() if line.rstrip('\n')]
    return ALLOWED_CLIENTS


def get_watcher_key(path, name):
    if not path.exists():
        path.touch(mode=0o644)
        return
    dotenv_as_dict = OrderedDict(parse_dotenv(str(path)))
    return dotenv_as_dict.get(name)


def set_env_key(path, key, value):
    if not path.exists():
        path.touch(mode=0o644)
        default_user = get_default_user()
        if Path('/etc', 'sera', 'env') != path and getpwuid(getuid()).pw_name != default_user:
            chown(str(path), user=default_user)
    return set_key(str(path), key, value, quote_mode="auto")[0]


def keygen(path, write=True):
    if write:
        if not path.exists():
            path.touch(mode=0o700)
            default_user = get_default_user()
            if Path('/etc', 'sera', 'env') != path and getpwuid(getuid()).pw_name != default_user:
                chown(str(path), user=default_user)

    private_key = PrivateKey.generate()
    public_key = private_key.public_key
    ascii_sk = urlsafe_b64encode(bytes(private_key)).decode('ascii')
    ascii_pk = urlsafe_b64encode(bytes(public_key)).decode('ascii')

    if write:
        set_key(
            str(path),
            'SERA_CLIENT_PRIVATE_KEY',
            ascii_sk,
            'auto')

        set_key(
            str(path),
            'SERA_CLIENT_PUBLIC_KEY',
            ascii_pk,
            'auto')

    return ascii_pk, ascii_sk


def encrypt(msg, recipient_key, private_key='', encoding='utf-8'):
    """Encrypt a message with the given recipient public key"""

    private_key = private_key or getenv('SERA_CLIENT_PRIVATE_KEY')
    skey = PrivateKey(private_key, URLSafeBase64Encoder)
    rkey = PublicKey(recipient_key, URLSafeBase64Encoder)
    msg = bytes(msg, encoding)
    box = Box(skey, rkey)
    nonce = random(Box.NONCE_SIZE)
    return box.encrypt(msg, nonce)


def decrypt(msg, sender_key, private_key='', encoding='utf-8'):
    """Decrypt a message with the given private key or SERA_CLIENT_PRIVATE_KEY"""
    private_key = private_key or getenv('SERA_CLIENT_PRIVATE_KEY')
    skey = PrivateKey(private_key, URLSafeBase64Encoder)
    pkey = PublicKey(sender_key, URLSafeBase64Encoder)
    box = Box(skey, pkey)
    return box.decrypt(msg).decode('utf-8')


