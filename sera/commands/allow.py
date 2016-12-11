import click
import requests
import time

from .main import main, lprint

from ..sera import remote, run
from ..settings import RESET_TIME
from ..utils import get_ip_address


@main.command()
@click.pass_context
@click.option('--delay', '-d', type=int, default=0)
@click.argument('from_ip', required=False)
def disallow(ctx, delay, from_ip):
    """Delete allowed connection from ip address"""

    verbosity = ctx.obj.get('verbosity')
    if not from_ip:
        ctx.params['from_ip'] = from_ip = requests.get(
            'http://ipinfo.io').json().get('ip')
    if verbosity:
        click.echo('ufw delete allow from %s' % from_ip)
    args = ['delete', 'allow', 'from', from_ip]
    if ctx.obj['local']:
        time.sleep(delay)
        out = run('ufw', args)
    else:
        out = remote('disallow', ctx)
    return lprint(ctx, out)


@main.command()
@click.pass_context
@click.option('--delay', '-d', type=int, default=RESET_TIME)
@click.argument('from_ip', required=False)
def allow(ctx, delay, from_ip):
    """Open firewall connection from ip address"""

    verbosity = ctx.obj.get('verbosity')
    if not from_ip:
        ctx.params['from_ip'] = from_ip = requests.get(
            'http://ipinfo.io').json().get('ip')
    if verbosity:
        click.echo('ufw allow from %s' % from_ip)
    args = ['allow', 'from', from_ip]
    if ctx.obj['local']:
        out = run('ufw', args)
        if not out.returncode:
            ip_addr = get_ip_address(from_ip)
            out.subcommand = disallow
            out.params = {'delay': delay, 'from_ip': from_ip}
            out.stdout += 'Resetting firewall on %s in %s seconds' % (ip_addr, str(RESET_TIME))
    else:
        out = remote('allow', ctx)
    return lprint(ctx, out)
