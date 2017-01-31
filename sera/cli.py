# -*- coding: utf-8 -*-
# flake8: noqa
import pkg_resources

import click
from pprint import pprint


from .commands.main import main

from .commands.echo import echo
from .commands.install import install
from .commands.addrevoke import add, revoke
from .commands.allow import allow, disallow
from .commands.end import end
from .commands.export import export
from .commands.watch import watch
from .commands.symlink import symlink
from .commands.create import signature, keypair, access
from .commands.crypt import encrypt, decrypt

sources = [main]
plugins = {}
for ep in pkg_resources.iter_entry_points(group='sera.collection'):
    sources.append(ep.load())

for ep in pkg_resources.iter_entry_points(group='sera.subcommand'):
    plugins[ep.name] = ep.load()

cli = click.CommandCollection(sources=sources)

