===============================
Sera
===============================


.. image:: https://img.shields.io/pypi/v/sera.svg
        :target: https://pypi.python.org/pypi/sera

.. image:: https://img.shields.io/travis/bretth/sera.svg
        :target: https://travis-ci.org/bretth/sera

.. image:: https://readthedocs.org/projects/sera/badge/?version=latest
        :target: https://sera.readthedocs.io/en/latest/?badge=latest
        :alt: Documentation Status

.. image:: https://pyup.io/repos/github/bretth/sera/shield.svg
     :target: https://pyup.io/repos/github/bretth/sera/
     :alt: Updates


The only secure port is a closed one. Execute click commands on a remote server without requiring a vpn, open inbound ports, or port knocking. This is pre-release software, python >= 3.5 and currently useful for Ubuntu based servers only.

Introduction
-------------
Sera is a client server commandline program that allows the client to invoke 'click' commands with end-to-end encryption over a transport on a 'watcher' host. Click is a commandline library for python.

For security, rather than listen for commands, the Sera 'watcher' polls the transport (currently only AWS SQS) for commands to execute and returns the output on a sender queue.

Currently the only useful command is the Sera *allow* command which will temporarily enable ufw to allow traffic from your current public ip address, but it is intended that Sera leverage saltstack for much more powerful configuration and orchestration either to control a master or to control masterless minions.

Essentially Sera layers a limited api over your server that can't be targeted by direct attacks, and means you won't need ssh or a vpn to access a server. Conceptually it is similar to salt but uses AWS SQS as transport instead of ZeroMQ. This means you can leverage the scaling and security of the battle tested AWS SQS at low cost.

Features
---------

- public key encryption over the ssl transport with pynacl
- clients are restricted to the available click commands
- watchers use a restricted AWS keypair that is limited to receiving and sending messages on known or guessable queue names
- pluggable transport

Goals
------

- wrap salt-call and salt commands
- a configurable list of commands that clients are allowed to invoke
- package for apt
- a configurable list of clients that can invoke commands on the watcher
- optionally use sudo with password instead of root user on watcher
- pluggable click commands
- target groups of watchers with AWS SNS
- glob '*' targeting of watchers
- integrate s3 and others for file 'upload' handling

Installation
-------------

On a macOS client within a python >= 3.5 virtual env::

    pip install git+https://github.com/bretth/sera#egg=sera

On an Ubuntu 16.04 server the pynacl lib needs building::

    sudo apt install build-essential libffi-dev python3-dev
    
Install the general python setup/install tools::

    sudo apt install python3-setuptools python3-pip python3-wheel
    
For the development version install git::

    sudo apt install git

Install sera itself:: 

    sudo pip3 install git+https://github.com/bretth/sera#egg=sera
    
Install a systemd sera.service file at /etc/systemd/service::

    sudo sera install service

Usage
--------------

On the client create an encryption keypair and install to ~/.sera/env::

    sera keygen
    
Get an AWS api access, secret keypair with permission to create policy, iam users, and groups then install into the env::
    
    sera export SERA_ACCESS_KEY=[AWS access key]
    sera export SERA_SECRET_KEY=[AWS secret key]

Install your aws region in the env file::

    sera export SERA_REGION=[your AWS region] 

Let sera create an AWS api access and secret keypair with restricted access to SQS::

    sera create_provider_keys

On the server install env settings in /etc/sera/env (by using sudo)::

    sudo sera keygen
    sudo sera export SERA_ACCESS_KEY=[AWS access key]
    sudo sera export SERA_SECRET_KEY=[AWS secret key]
    
Get your AWS region code from http://docs.aws.amazon.com/general/latest/gr/rande.html ::

    sudo sera export SERA_REGION=[your AWS region] 

To allow client access their public keys need to be added to /etc/sera/known_clients::

    sudo sera add [the public key from client keygen]
    
Enable & start the service::

    sudo systemctl daemon-reload
    sudo systemctl enable sera
    sudo systemctl start sera

Security notes
--------------

- The nacl encryption private keys are never transmitted
- all messages between the client and watcher are encrypted after the initial public key exchange
- watchers can only receive commands from known clients
- the boto3 library uses verified ssl encryption over the top of the nacl encryption
- AWS SQS is limited to 256KB message size
- watcher aws keypair cannot delete messages, list or create queues.


Credits
---------

This package was created with Cookiecutter_ and the `audreyr/cookiecutter-pypackage`_ project template.

.. _Cookiecutter: https://github.com/audreyr/cookiecutter
.. _`audreyr/cookiecutter-pypackage`: https://github.com/audreyr/cookiecutter-pypackage

