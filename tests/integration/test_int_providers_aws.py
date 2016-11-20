# from pprint import pprint

from sera.providers.aws import Message


class TestAWSProvider(object):

    def test_get_missing_endpoint(self, client, a_name):
        url = client.get_endpoint(a_name)
        assert not url

    def test_get_endpoint(self, client, endpoint):
        name, url = endpoint
        assert url == client.get_endpoint(name)

    def test_create_endpoint(self, client, endpoint_name):
        assert endpoint_name in client.create_endpoint(endpoint_name)

    def test_send_message(self, master, endpoint_name):
        master.client.send_message(name=endpoint_name, msg='test')
        message = master.client.sqs.receive_message(QueueUrl=master.url)
        assert message['Messages']

    def test_receive_message(self, master):
        msg = master.client.receive_message()
        assert type(msg) == Message
        assert msg.body == 'test'
