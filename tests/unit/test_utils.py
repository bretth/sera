import os
# import pytest

from sera.utils import keygen, encrypt, decrypt, get_default_envpath
from dotenv import get_key
from pathlib import Path

SECRET_KEY1 = 'mWxBUK-aDh6qZRhdFROhTyiQVdk2pZwqwq-hq4-5elw='
PUBLIC_KEY1 = 'b1ZfANMSxRJwqtkJK4DwLoL7wCl8-Rjl8aPEc-co4TU='
SECRET_KEY2 = 'dlYwsLBxbmjfzegB0bMvr15I4WUKmfjcMAXUxdHAkoU='
PUBLIC_KEY2 = 'enLttA6OYJ1ctH3cDRi21uLwTXWRLC_jhY_e952lt3E='


def test_keygen():
    keygen('.testenv', write=True)
    private_key = get_key('.testenv', 'SERA_PRIVATE_KEY')
    print(private_key)
    public_key = get_key('.testenv', 'SERA_PUBLIC_KEY')
    print(public_key)


def teardown_function():
    try:
        os.remove('.testenv')
    except FileNotFoundError:
        pass


def test_encrypt_decrypt():
    msg = encrypt('test', recipient_key=PUBLIC_KEY1, private_key=SECRET_KEY2)
    assert msg
    msg2 = decrypt(msg, PUBLIC_KEY2, SECRET_KEY1)
    assert msg2 == 'test'


def test_get_default_env(dotenv_file):
    path = get_default_envpath()
    assert path == str(dotenv_file)