# conftest.py
import json
from os import getenv
from uuid import uuid4
import pytest

import boto3
from botocore.exceptions import ClientError
from sera.providers.aws import AWSProvider
from sera.sera import Host
from sera.utils import encrypt


def sqs():
    return boto3.client(
        'sqs',
        region_name=getenv('SERA_REGION'),
        aws_access_key_id=getenv('SERA_ACCESS_KEY'),
        aws_secret_access_key=getenv('SERA_SECRET_KEY'))


@pytest.fixture
def a_name():
    return '-'.join(['test', str(uuid4())])


@pytest.fixture(scope='module')
def client():
    return AWSProvider(namespace='')


@pytest.fixture
def master():
    host = Host.get(a_name(), create=True)
    host.client.send_message(host.name, msg='test')
    yield host
    sqs().delete_queue(QueueUrl=host.url)


@pytest.fixture
def endpoint():
    name = a_name()
    url = sqs().create_queue(
        QueueName=name,
        Attributes={'ReceiveMessageWaitTimeSeconds': '0'})['QueueUrl']
    yield name, url
    sqs().delete_queue(QueueUrl=url)


@pytest.fixture
def endpoint_name():
    """
    A name that gets a corresponding queue torn down but doesn't create it
    """
    name = a_name()
    yield name
    try:
        url = sqs().get_queue_url(QueueName=name)['QueueUrl']
        sqs().delete_queue(QueueUrl=url)
    except ClientError:
        pass


@pytest.fixture
def host_and_a_key():
    """
    master Host queue with a msg (watcher public key) on it
    """
    public_key = 'enLttA6OYJ1ctH3cDRi21uLwTXWRLC_jhY_e952lt3E='
    host = Host.get(a_name(), create=True)
    # put a public key on the master host queue
    host.client.send_message(
        host.name, msg=json.dumps('public_key %s' % public_key))
    yield host, public_key
    sqs().delete_queue(QueueUrl=host.url)


@pytest.fixture
def host():
    """
    master host
    """
    host = Host.get(a_name(), create=True)
    yield host
    sqs().delete_queue(QueueUrl=host.url)


@pytest.fixture
def host_with_cmd():
    """
    Host with a command on the queue
    """
    host = Host.get(a_name(), create=True)
    pkey = getenv('SERA_CLIENT_PUBLIC_KEY')
    cmd = {'name': 'echo'}
    encrypted = encrypt(json.dumps(cmd), pkey, getenv('SERA_CLIENT_PRIVATE_KEY'))
    sqs().send_message(
        QueueUrl=host.url,
        MessageBody=json.dumps('decrypt %s' % pkey),
        MessageAttributes={
            'Sender': {'StringValue': host.uid, 'DataType': 'String'},
            'Encrypted': {'BinaryValue': encrypted, 'DataType': 'Binary'}
        })
    yield host, cmd['name'], pkey
    sqs().delete_queue(QueueUrl=host.url)
