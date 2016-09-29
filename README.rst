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


The only secure port is a closed one. Execute click commands on a remote server without requiring a vpn, open inbound ports, or port knocking. This is pre-release software, python3 and currently useful for Ubuntu based servers only.

Introduction
-------------
Sera is a client server commandline program that allows the client to invoke 'click' commands with end-to-end encryption over a transport on a 'watcher' host. Click is a commandline library for python.

For security, rather than listen for commands, the Sera 'watcher' polls the transport (currently only AWS SQS) for commands to execute and returns the output on a sender queue.

Currently the only useful command is the Sera *allow* command which will temporarily enable ufw to allow traffic from your current public ip address, but it is intended that Sera leverage saltstack for much more powerful configuration and orchestration either to control a master or to control masterless minions.

Essentially Sera layers a limited api over your server that can't be targeted by direct attacks, and means you won't need ssh or a vpn to access a server. Conceptually it is similar to salt but uses AWS SQS as transport instead of ZeroMQ. This means you can leverage the scaling and security of the battle AWS SQS at low cost.

Features
--------

 - public key encryption over the ssl transport with pynacl
 - clients are restricted to the available click commands
 - watchers use a restricted AWS keypair that is limited to receiving and sending messages on a queue
 - pluggable transport

Goals
------

- wrap salt-call and salt commands
- a configurable list of commands that a client can invoke
- package for apt
- a configurable list of clients that can issue commands on the watcher
- optionally use sudo with password instead of root for security in the event of compromised client
- pluggable click commands
- target groups of watchers with AWS SNS
- glob '*' targeting of watchers

Installation
-------------

To come.

Security notes
--------------
The main known weaknesses are:

- In that event a compromised server AWS keypair can guess the name of other watchers then they can send commands to those watches. This can be mitigated by using difficult to guess watcher/host names.

- Client and server communicate by public key encryption using the pynacl library. On first contact they swap public keys, which means potentially with a compromised AWS keypair a malicious client could get in first assuming they know the watcher/host name.

- Sera is intended to run as root user so a compromised client or server aws keypair can issue any command to the server.


Credits
---------

This package was created with Cookiecutter_ and the `audreyr/cookiecutter-pypackage`_ project template.

.. _Cookiecutter: https://github.com/audreyr/cookiecutter
.. _`audreyr/cookiecutter-pypackage`: https://github.com/audreyr/cookiecutter-pypackage

