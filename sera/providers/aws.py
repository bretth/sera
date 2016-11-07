
import logging
import re
import os
from datetime import datetime

from dateutil.tz import tzlocal
import boto3
from botocore.exceptions import ClientError

from ..expiringdict import ExpiringDict

logger = logging.getLogger(__name__)

ReceiveMessageWaitTimeSeconds = 0  # let the clients set wait time instead of the queue
MessageRetentionPeriod = 60  # shortest period possible on aws
VisibilityTimeout = MessageRetentionPeriod+60  # ensure the message is only seen once

url_pattern = re.compile('[^a-zA-Z0-9_-]+')
ENDPOINT_CACHE = None

# AWS SQS guarantees at least once but in practice may deliver twice
# regardless of retention period and visibility timeout so we want to cache received
# messageids to ensure we don't duplicate commands.
MSG_CACHE = ExpiringDict(VisibilityTimeout+60)

Q_NAMESPACE = 'Sera'
USERNAME = 'SeraWatcher'
GROUP = 'SeraWatchers'
POLICY_NAME = 'SeraReceiveSendGetQueue'
WATCHER_POLICY = """{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Sid": "1",
            "Effect": "Allow",
            "Action": [
                "sqs:GetQueueUrl",
                "sqs:ReceiveMessage",
                "sqs:SendMessage"
            ],
            "Resource": [
                "arn:aws:sqs:*"
            ]
        }
    ]
}"""

logger = logging.getLogger(__name__)


class Message(object):
    def __init__(self, uid, timestamp=0, body='', sender='', **kwargs):
        self.__dict__.update(kwargs)
        self.uid = str(uid)
        self.timestamp = int(timestamp)
        self.body = body
        self.sender = sender

    def __repr__(self):
        return '<%s %s %s>' % (self.__class__.__name__, self.datetimestamp, self.body)

    def __str__(self):
        return self.body

    @property
    def datetimestamp(self):
        if self.timestamp:
            return datetime.fromtimestamp(
                int(str(self.timestamp)[:10]), tz=tzlocal()).strftime('%d/%b/%Y:%H:%M:%S %z')


class AWSProvider(object):
    def __init__(
            self,
            region='',
            access_key='',
            secret_access_key='',
            namespace=None,
            **kwargs):
        global ENDPOINT_CACHE
        if not ENDPOINT_CACHE:
            ENDPOINT_CACHE = ExpiringDict(int(os.getenv('SERA_ENDPOINT_TTL', 60*60)))
        self.cache = ENDPOINT_CACHE
        self.name = 'AWS'
        self.endpoint = kwargs.get('endpoint')  # sera.Host
        self.sqs = boto3.client(
            'sqs',
            region_name=region or os.getenv('SERA_REGION'),
            aws_access_key_id=access_key or os.getenv('SERA_ACCESS_KEY'),
            aws_secret_access_key=secret_access_key or os.getenv('SERA_SECRET_KEY'))
        if namespace is None:  # allow '' to be set as a valid namespace
            namespace = os.getenv('SERA_NAMESPACE', 'Sera')
        kwargs.setdefault('namespace', namespace)
        kwargs.setdefault('ReceiveMessageWaitTimeSeconds', ReceiveMessageWaitTimeSeconds)
        kwargs.setdefault('MessageRetentionPeriod', MessageRetentionPeriod)
        kwargs.setdefault('VisibilityTimeout', VisibilityTimeout)
        self.__dict__.update(kwargs)

    def _sanitize(self, name):
        """Return a name with a namespace and limited to sqs max queue name length"""
        name = url_pattern.sub('-', name)
        if self.namespace:
            return '-'.join([self.namespace, name])[:80]
        return name[:80]

    @classmethod
    def create_provider_keys(
            cls,
            username=USERNAME,
            group=GROUP,
            policy_name=POLICY_NAME,
            policy=WATCHER_POLICY):
        """Create a provider user with permissions for the watcher to connect"""

        iam = boto3.client(
            'iam',
            region_name=os.getenv('SERA_REGION'),
            aws_access_key_id=os.getenv('SERA_ACCESS_KEY'),
            aws_secret_access_key=os.getenv('SERA_SECRET_KEY'))
        try:
            iam.create_user(UserName=username)
            keys = iam.create_access_key(UserName=username)
            access_key = keys.get('AccessKey', {}).get('AccessKeyId')
            secret_key = keys.get('AccessKey', {}).get('SecretAccessKey')
        except ClientError as e:
            access_key = secret_key = None
            code = e.response.get('Error', {}).get('Code', '')
            if code != 'EntityAlreadyExists':
                raise
        try:
            iam.create_group(GroupName=group)
        except ClientError as e:
            code = e.response.get('Error', {}).get('Code', '')
            if code != 'EntityAlreadyExists':
                raise
        try:
            iam.add_user_to_group(GroupName=group, UserName=username)
        except ClientError as e:
            code = e.response.get('Error', {}).get('Code', '')
            if code != 'EntityAlreadyExists':
                raise

        iam.put_group_policy(
            GroupName=group,
            PolicyName=policy_name,
            PolicyDocument=WATCHER_POLICY)
        return access_key, secret_key

    def create_endpoint(self, name):
        try:
            url = self.sqs.create_queue(
                QueueName=self._sanitize(name),
                Attributes={
                    'ReceiveMessageWaitTimeSeconds':
                    str(self.ReceiveMessageWaitTimeSeconds),
                    'MessageRetentionPeriod':
                    str(self.MessageRetentionPeriod),
                    'VisibilityTimeout':
                    str(self.VisibilityTimeout)})['QueueUrl']
        except ClientError as e:
            code = e.response.get('Error', {}).get('Code', '')
            logger.error('%s on create_queue %s' % (code, name))
            raise
        self.cache[name] = url
        return url

    def delete_endpoint(self, url):
        self.sqs.delete_queue(QueueUrl=url)

    def get_endpoint(self, name):
        queue_name = self._sanitize(name)
        url = self.cache.get(name)
        if not url:
            try:
                url = self.sqs.get_queue_url(QueueName=queue_name)['QueueUrl']
                self.cache[name] = url
            except ClientError as e:
                code = e.response.get('Error', {}).get('Code', '')
                if code == 'AWS.SimpleQueueService.NonExistentQueue':
                    logger.debug("%s queue doesn't exist" % queue_name)
                    return
                else:
                    raise
        logger.debug('get_endpoint %s' % str(url))
        return url

    def delete_message(self, uid):
        return self.sqs.delete_message(
            QueueUrl=self.endpoint.url,
            ReceiptHandle=uid)

    def receive_message(self, timeout=0):
        global MSG_CACHE
        if timeout > 20 or timeout < 0:  # aws max long poll
            timeout = 20
        msg = None
        while not msg or msg.get('MessageId') in MSG_CACHE:
            msg = self.sqs.receive_message(
                QueueUrl=self.endpoint.url,
                AttributeNames=['SentTimestamp'],
                MessageAttributeNames=['Sender', 'Encrypted'],
                WaitTimeSeconds=timeout,
                MaxNumberOfMessages=1).get('Messages', [None])[0]
        if msg and msg['MessageId'] not in MSG_CACHE:
            message = Message(
                uid=msg['ReceiptHandle'],
                timestamp=msg['Attributes']['SentTimestamp'],
                body=msg['Body'],
                sender=msg['MessageAttributes'].get('Sender', {}).get('StringValue', ''),
                encrypted=msg['MessageAttributes'].get('Encrypted', {}).get('BinaryValue', ''))
            return message
        return

    def send_message(self, name, msg, attributes={}):
        to = self.endpoint.get(
            name, create=self.endpoint.creator)
        msg_attrs = {}
        msg_attrs['Sender'] = self.endpoint.uid
        msg_attrs.update(attributes)
        for attr, value in msg_attrs.items():
            if type(value) != str:
                msg_attrs[attr] = {'BinaryValue': value, 'DataType': 'Binary'}
            else:
                msg_attrs[attr] = {'StringValue': value, 'DataType': 'String'}
        logger.info('sqs.send_message(%s, ...)' % to.url)
        response = self.sqs.send_message(
            QueueUrl=to.url,
            MessageBody=msg,
            MessageAttributes=msg_attrs)

        return response
