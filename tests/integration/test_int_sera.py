# test_sera

from os import getenv
from sera.sera import Host


class TestHost(object):

    def test_get_absent_queue(self, a_name):
        assert not Host.get(a_name)

    def test_get_a_queue(self, endpoint):
        name, url = endpoint
        host = Host.get(name, namespace='')
        assert host.url == url

    def test_get_create_a_queue(self, endpoint_name):
        host = Host.get(endpoint_name, create=True)
        assert host.uid == endpoint_name
        assert endpoint_name in host.url

    def test_exchange_keys(self, host_and_a_key, endpoint):
        host, public_key = host_and_a_key
        name = endpoint[0]

        watcher_key = host.exchange_keys(name)
        assert watcher_key == public_key

    def test_send_cmd_with_response(self, host):
        cmd = 'echo'
        pkey = getenv('SERA_PUBLIC_KEY')
        # send to myself
        resp = host.send(host.name, cmd, {}, pkey)
        assert cmd == resp.name

    def test_send_cmd_no_response(self, host, endpoint):
        name = endpoint[0]
        cmd = 'echo'
        public_key = 'enLttA6OYJ1ctH3cDRi21uLwTXWRLC_jhY_e952lt3E='
        response = host.send(name, cmd, {}, public_key, timeout=0)
        assert response is None

    def test_receive_cmd(self, host_with_cmd):
        host, cmd, pkey = host_with_cmd
        resp = host.receive(timeout=0)
        assert pkey == resp.public_key
        assert cmd == resp.name
