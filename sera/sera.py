import logging
import re
from os import getenv
from subprocess import run as _run, PIPE, CompletedProcess
import json
import importlib
import time

from nacl.exceptions import CryptoError

from .utils import encrypt, decrypt

logger = logging.getLogger(__name__)

START_TIME = 0
DEFAULT_CLIENT = 'sera.providers.aws.AWSProvider'
DEFAULT_TIMEOUT = 20
Q_NAMESPACE = 'Sera'

url_pattern = re.compile('[^a-zA-Z0-9_-]+')


class RemoteCommand(CompletedProcess):
    def __init__(self, **kwargs):
        self.__dict__['host'] = kwargs.pop('host', None)
        self.__dict__['public_key'] = kwargs.pop('public_key', None)
        self.__dict__['name'] = kwargs.pop('name', None)
        self.__dict__['params'] = kwargs.pop('params', None)
        self.__dict__['subcommand'] = kwargs.pop('subcommand', None)
        kwargs.setdefault('returncode', None)
        kwargs.setdefault('args', ())
        super().__init__(**kwargs)

    @property
    def name(self):
        return self.__dict__.get('name', '')

    @property
    def params(self):
        return self.__dict__.get('params', {})

    @property
    def subcommand(self):
        return self.__dict__.get('subcommand', None)

    @property
    def host(self):
        return self.__dict__.get('host', '')

    @property
    def public_key(self):
        return self.__dict__.get('public_key')


def get_client():
    try:
        *modules, class_name = getenv('SERA_CLIENT', DEFAULT_CLIENT).split('.')
    except ValueError:
        raise Exception(
            "A custom SERA_CLIENT provider must be a fully qualified class"
            "e.g. sera.providers.aws_sqs.AWSProvider")

    module_name = '.'.join(modules)
    module = importlib.import_module(module_name)
    return getattr(module, class_name)


def run(cmd, args=None):
    """
    Run command as sudo user (to log command)
    """
    cmd = ['sudo', '-n', cmd]  # avoid prompting for sudo password
    if args:
        cmd += list(args)
    return _run(
            cmd,
            stdout=PIPE,
            stderr=PIPE,
            universal_newlines=True,
            timeout=60*12)


def remote(cmd, ctx):
    watcher = ctx.obj['watcher']
    master = ctx.obj['master']
    return master.send(
        watcher.name, cmd, ctx.params, ctx.obj['watcher_key'], ctx.obj['timeout'])


class BaseEndpoint(object):

    def __init__(self, uid, url='', client=None, creator=False):
        self.uid = str(uid)
        self.url = url
        # clients and endpoints point to each other
        if client:
            client.endpoint = self
        self.creator = creator
        self.client = client

    def __repr__(self):
        return '<%s %s>' % (self.__class__.__name__, self.uid)

    def __str__(self):
        return self.url

    @property
    def name(self):
        """Return a url friendly name"""
        return url_pattern.sub('-', self.uid)


class Host(BaseEndpoint):

    @classmethod
    def get(cls, name, create=False, namespace=None):
        client = get_client()(namespace=namespace)
        url = client.get_endpoint(name)
        if not url and create:
            url = client.create_endpoint(name)
        if url:
            return cls(name, url, client, creator=create)
        return

    def exchange_keys(self, name, timeout=DEFAULT_TIMEOUT):
        cmd = 'public_key %s' % getenv('SERA_CLIENT_PUBLIC_KEY', '')
        remote = self.send(name, cmd)
        watcher_key = None
        if remote and remote.name.startswith('public_key'):
            watcher_key = remote.public_key
        return watcher_key

    def send(
            self,
            name,
            cmd='',
            params='',
            recipient_key=None,
            timeout=-1,
            await_response=True,
            stdout='',
            stderr='',
            returncode=None):
        payload = {}
        if recipient_key:  # encrypt
            kwargs = {
                'params': params, 'name': cmd,
                'stdout': stdout, 'stderr': stderr, 'returncode': returncode}
            encrypted = encrypt(json.dumps(kwargs), recipient_key, getenv('SERA_CLIENT_PRIVATE_KEY'))
            payload = {'Encrypted': encrypted}
            cmd = 'decrypt %s' % getenv('SERA_CLIENT_PUBLIC_KEY')
        logger.debug('Host.client.send_message(%s, %s, ...)' % (name, str(cmd)))
        self.client.send_message(name, json.dumps(cmd), payload)
        if await_response:
            return self.receive(timeout)
        return

    def receive(self, timeout=-1):
        delay = 0
        max_delay = int(getenv('SERA_MAX_DELAY', '20'))
        start = time.time()
        while True:
            msg = self.client.receive_message(timeout)
            if msg:
                break
            duration = time.time() - start
            if timeout > -1 and duration > timeout:
                return

            # limit the polling on queues to an acceptable threshold
            time.sleep(delay)
            if delay < max_delay:
                delay += 1

        if ' ' in msg.body:
            body, senders_key = json.loads(msg.body).split(' ')
        else:
            body = msg.body
            senders_key = None
        if body == 'decrypt':
            try:
                kwargs = json.loads(
                    decrypt(msg.encrypted, senders_key, getenv('SERA_CLIENT_PRIVATE_KEY')))
            # if the message is unencrypted it will raise a ValueError trying to extract a NONCE
            except (ValueError, CryptoError) as err:
                logger.warning('Failed to decrypt msg')
                logger.warning(msg)
                logger.warning(str(err))
                return

            logger.debug(
                'RemoteCommand(host=%s, public_key=%s, name=%s' %
                (msg.sender, str(senders_key), kwargs.get('name')))
            return RemoteCommand(host=msg.sender, public_key=senders_key, **kwargs)
        logger.debug(
            'RemoteCommand(host=%s, public_key=%s, name=%s, ...)' %
            (msg.sender, str(senders_key), body))
        return RemoteCommand(host=msg.sender, name=body, public_key=senders_key)
