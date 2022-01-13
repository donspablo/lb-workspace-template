#!/usr/bin/env python3
from __future__ import print_function
import os
import re
import socket
from collections import defaultdict
from config import read_config
from utils import setup_logging, run, DEVNULL

SSH_CONFIG = os.path.join(os.path.dirname(__file__), 'ssh_config')
KNOWN_HOSTS = os.path.join(os.path.dirname(__file__), '.known_hosts')
config = read_config()

log = setup_logging(config['outputPath'])


def parse_spec(spec):
    m = re.match(
        r'^(?P<hostid>[a-zA-Z0-9-.]+)(:(?P<port>[0-9]+))?'
        r'(/(?P<limit>[0-9]+))?(,(?P<options>[^ ]+))?$', spec)
    if not m:
        raise ValueError('Cannot parse HOSTSPEC {!r}'.format(spec))
    spec = m.groupdict()
    spec['port'] = int(spec['port'] or 3632)
    spec['limit'] = int(spec['limit'] or 4)
    spec['options'] = (spec['options'] or '').split(',')
    return spec


def write_spec(spec):
    s = '{hostid}:{port}/{limit}'.format(**spec)
    return s if not spec['options'] else (s + ',' + ','.join(spec['options']))


def is_port_open(host, port, test_distcc=False, timeout=0.2):
    """Check if we can open a port on a host.

    Optionally, try to do a handshake with a distcc server.

    """
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.settimeout(timeout)
            sock.connect((host, port))
            if test_distcc:
                sock.sendall(b'*')
                return sock.recv(1) == b'*'
    except (ConnectionError, socket.timeout):
        return False
    return True


def reachable(host, port=None, timeout=0.2):
    if port is not None:
        return is_port_open(host, port, timeout=timeout)
    else:
        # If port is not given, check that the host is up and reachable.
        # We don't check the distcc port since it's possible that the
        # host is up but the distcc server is down.
        return run(
            ['timeout', str(timeout), 'ping', '-c1', '-q', host],
            check=False).returncode == 0


def have_valid_ticket():
    try:
        return have_valid_ticket.cache
    except AttributeError:
        code = run(['klist', '-s'], check=False).returncode
        have_valid_ticket.cache = code == 0
        return have_valid_ticket.cache


found_hosts = {}
proxied_hosts = defaultdict(list)
for host in config['distccHosts']:
    spec = parse_spec(host['spec'])
    if 'auth' in spec['options']:
        if not have_valid_ticket():
            log.warning('No valid kerberos ticket, disabling distcc host ' +
                        host['spec'])
            continue
    # Check the "networkProbe" if defined, otherwise check the host directly.
    # The latter has the disadvantage that if the host down but we're on the
    # right network, we'll (unsuccessfully) try to proxy it.
    if reachable(host.get('networkProbe', spec['hostid'])):
        # The host is directly reachable
        # if is_port_open(spec['hostid'], spec["port"], test_distcc=True):
        found_hosts[host['spec']] = spec['limit']
    else:
        # The host needs to be proxied
        new_spec = {
            # "localhost" has a special meaning for distcc -> use "127.0.0.1"
            'hostid':
            '127.0.0.1',
            'port':
            host['localPort'],
            'limit':
            spec['limit'],
            'options': [
                opt if opt != 'auth' else ('auth=' + spec['hostid'])
                for opt in spec['options']
            ]
        }
        if reachable(new_spec['hostid'], new_spec['port']):
            log.debug(f"distcc server {spec['hostid']} is already proxied")
            found_hosts[write_spec(new_spec)] = spec['limit']
        else:
            # collect hosts to proxy
            proxied_hosts[host['gateway']].append(
                (write_spec(new_spec), host['spec'], host['localPort'],
                 spec['hostid'], spec['port'], spec['limit']))

if proxied_hosts:
    kerberos_user = run(
        "klist | grep -oP 'Default principal: \\K.+(?=@)'",
        shell=True).stdout.strip()

for gateway, hosts in proxied_hosts.items():
    log.info('Starting ssh port forwarding for distcc hosts {}...'.format(
        ' '.join(h[1] for h in hosts)))
    forwards = sum((['-L', '{}:{}:{}'.format(local, host, port)]
                    for _, _, local, host, port, _ in hosts), [])
    cmd = [
        'ssh', '-f', '-N', '-F', SSH_CONFIG, '-o', 'BatchMode=yes', '-o',
        'ExitOnForwardFailure=yes', '-o', 'UserKnownHostsFile=' + KNOWN_HOSTS,
        '-o', 'LogLevel=ERROR'
    ] + forwards + ['{}@{}'.format(kerberos_user, gateway)]
    code = run(
        cmd,
        # decouple stdout so that bash (the command substitution) does
        # not wait forever for the stdout of this process
        stdout=DEVNULL,
        # do not try to capture stderr (for the log) as .communicate()
        # seems hang in that case
        capture_stderr=False,
        check=False).returncode
    if code == 0:
        for h in hosts:
            found_hosts[h[0]] = h[5]
        log.info('...done.')
    else:
        log.error(f'Failed to forward ports via {gateway}.')

n_slots = sum(found_hosts.values())
found_hosts = sorted(found_hosts.keys())
if not found_hosts:
    log.error("No distcc hosts found!")
    exit(1)

# Specify how many jobs that cannot be run remotely can be run concurrently
# on the local machine
n_localslots = config['distccLocalslots']
found_hosts.append('--localslots={}'.format(n_localslots))
# Specify how many preprocessors will run in parallel on the local machine.
# (only relevant for non-pump mode)
n_localslots_cpp = config['distccLocalslotsCpp']
found_hosts.append('--localslots_cpp={}'.format(n_localslots_cpp))

if config['distccRandomize']:
    found_hosts.append('--randomize')

print(f"""
export DISTCC_HOSTS="{' '.join(found_hosts)}"
export DISTCC_PRINCIPAL="{config['distccPrincipal']}"
export DISTCC_SKIP_LOCAL_RETRY=1
export DISTCC_IO_TIMEOUT=300
export BUILDFLAGS="$BUILDFLAGS -j{n_slots*5//4}"
""")
# Note that the last line has no effect when BUILDFLAGS is passed to make.
# In that case the variable goes via MAKEFLAGS.

# TODO add cpp conditionally on USE_DISTCC_PUMP? Does non-pump work now?
# TODO what if you're compiling from one of the distcc hosts?
