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


The only secure port is a closed one. Execute click commands on a remote server without requiring a vpn, open inbound ports, or port knocking. This is pre-release software, python3 and currently intended for Ubuntu based servers only.

Introduction
-------------
Sera is a client server commandline program that allows the client to issue 'click' commands with end-to-end encryption over a transport to a 'watcher' host. Click is a commandline library for python.

The Sera 'watcher' polls the transport (currently only AWS SQS) for commands to execute and returns the output.

Currently the Sera *allow* command will temporarily enable ufw to allow traffic from your current public ip address, but it is intended that Sera leverage saltstack for much more powerful configuration and orchestration.

Essentially Sera exposes a limited api to your server that can't be targetted by direct attacks.

Features
--------

 * public key encryption over the ssl transport with pynacl
 * clients are restricted to the available click commands
 * servers use a restricted AWS keypair that is limited to receiving and sending messages on a queue
 * pluggable transport

Goals
------

- wrap salt-call and salt commands
- a configurable list of commands that a client can invoke
- package for apt
- a configurable list of clients that can issue commands on the watcher
- optionally use sudo with password instead of root for security in the event of compromised client
- pluggable click commands

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

