from pprint import pprint
from uuid import uuid4
from unittest.mock import patch
from dotenv import load_dotenv
import pytest

import boto3

from sera.providers.aws_sqs import AWSProvider
from sera.sera import exchange_keys, send_cmd, watch_cmd
load_dotenv('.env')


@pytest.fixture
def public_key():
    # setup
    master = str(uuid4())
    watcher = str(uuid4())
    client = AWSProvider.connect(watcher, master, create=True)

    # put a public key on the master queue
    client.send_message(
        recipient=master,
        sender=watcher,
        msg='public_key %s' % 'enLttA6OYJ1ctH3cDRi21uLwTXWRLC_jhY_e952lt3E='
    )
    yield client, watcher, master

    # teardown
    client.sqs.delete_queue(QueueUrl=client.watcher.url)
    client.sqs.delete_queue(QueueUrl=client.master.url)


def test_exchange_keys(public_key):
    client, watcher, master = public_key
    watcher_key = exchange_keys(client, watcher, master, timeout=20)
    assert watcher_key == 'enLttA6OYJ1ctH3cDRi21uLwTXWRLC_jhY_e952lt3E='



@patch('sera.sera.get_watcher_key', return_value='enLttA6OYJ1ctH3cDRi21uLwTXWRLC_jhY_e952lt3E=')
def test_send_cmd(mock):
    watcher_key = watch_cmd(watcher)
    assert watcher_key == 'enLttA6OYJ1ctH3cDRi21uLwTXWRLC_jhY_e952lt3E='








