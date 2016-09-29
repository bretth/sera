from pprint import pprint
import os
from uuid import uuid4
# import pytest
from dotenv import load_dotenv

import boto3
from sera.providers.aws_sqs import AWSProvider, AWSQueue

load_dotenv('.env')


class TestAWSQueue(object):

    def test_name(self):
        q = AWSQueue('sera.example.com', 'db')
        assert q.name == 'db-sera-example-com'


class TestAWSProviderCreate(object):
    @classmethod
    def setup_class(cls):
        cls.client = AWSProvider()
        cls.queue = AWSQueue(str(uuid4()))

    def test_create_queue(self):
        queue = self.client.create_queue(self.queue)
        pprint(queue.url)
        assert self.queue.name in queue.url

    @classmethod
    def teardown_class(cls):
        cls.client.sqs.delete_queue(QueueUrl=cls.queue.url)


class TestAWSProviderLoad(object):
    @classmethod
    def setup_class(cls):
        cls.client = AWSProvider()
        cls.queue = AWSQueue(str(uuid4()))
        cls.created_q = cls.client.create_queue(AWSQueue(str(uuid4())))

    def test_load_nonexistent_queue(self):
        queue = self.client.load_queue('role', self.queue)
        assert not queue

    def test_load_actual_queue(self):
        created = self.client.load_queue('role', self.created_q)
        assert created is True
        assert self.client.queues['role'].url == self.created_q.url

    @classmethod
    def teardown_class(cls):
        cls.client.sqs.delete_queue(QueueUrl=cls.created_q.url)


class TestAWSProvider(object):

    @classmethod
    def setup_class(cls):
        cls.urls = []
        cls.client = None
        cls.watcher = str(uuid4())
        cls.master = str(uuid4())

    def test_connect(self):
        self.client = AWSProvider.connect(self.watcher, self.master, create=True)
        assert self.watcher in self.client.watcher.url
        assert self.master in self.client.master.url
        self.urls = [self.client.watcher.url, self.client.master.url]

    @classmethod
    def teardown_class(cls):
        for url in cls.urls:
            cls.client.sqs.delete_queue(QueueUrl=url)


class TestAWSProviderCreateProviderUser(object):

    @classmethod
    def setup_class(cls):
        cls.name = 'TestSera'
        cls.group = 'TestSeraGroup'
        cls.policy_name = 'TestSeraPolicy'
        cls.access_key = None
        cls.iam = boto3.client(
            'iam',
            region_name=os.getenv('SERA_REGION'),
            aws_access_key_id=os.getenv('SERA_ACCESS_KEY'),
            aws_secret_access_key=os.getenv('SERA_SECRET_KEY'))

    def test_create_provider_keys(self):
        access_key, secret_key = AWSProvider.create_provider_keys(
            username=self.name,
            group=self.group,
            policy_name=self.policy_name)
        assert access_key
        assert secret_key
        self.iam.delete_access_key(UserName=self.name, AccessKeyId=access_key)

    @classmethod
    def teardown_class(cls):
        cls.iam.delete_group_policy(
            GroupName=cls.group,
            PolicyName=cls.policy_name)
        cls.iam.remove_user_from_group(UserName=cls.name, GroupName=cls.group)
        access_keys = cls.iam.list_access_keys(UserName=cls.name).get('AccessKeyMetadata')
        for key in access_keys:
            cls.iam.delete_access_key(UserName=key['UserName'], AccessKeyId=key['AccessKeyId'])

        cls.iam.delete_user(UserName=cls.name)
        cls.iam.delete_group(GroupName=cls.group)


class TestAWSProviderSendMessage(object):

    @classmethod
    def setup_class(cls):
        cls.watcher = str(uuid4())
        cls.master = str(uuid4())
        cls.client = AWSProvider.connect(cls.watcher, cls.master, create=True)

    def test_send_message(self):
        response = self.client.send_message(recipient=self.watcher, sender=self.master, msg='test')
        pprint(response)
        assert response['ResponseMetadata']['HTTPStatusCode'] == 200

    @classmethod
    def teardown_class(cls):
        cls.client.sqs.delete_queue(QueueUrl=cls.client.watcher.url)
        cls.client.sqs.delete_queue(QueueUrl=cls.client.master.url)


class TestAWSProviderReceiveMessage(object):

    @classmethod
    def setup_class(cls):
        cls.watcher = str(uuid4())
        cls.master = str(uuid4())
        cls.client = AWSProvider.connect(cls.watcher, cls.master, create=True)
        cls.client.send_message(recipient=cls.watcher, sender=cls.master, msg='test2')

    def test_receive_messages(self):

        messages = self.client.receive_messages(self.watcher)
        pprint(messages[0])
        assert messages[0].body == 'test2'
        assert messages[0].sender.uid == self.master

    @classmethod
    def teardown_class(cls):
        cls.client.sqs.delete_queue(QueueUrl=cls.client.watcher.url)
        cls.client.sqs.delete_queue(QueueUrl=cls.client.master.url)
