#!/usr/bin/env python3
from __future__ import print_function
import sys

if sys.version_info < (2, 7):
    sys.exit("Python 2.7 or later is required.")

import argparse  # noqa: E402
import logging  # noqa: E402
import os  # noqa: E402
import shutil  # noqa: E402
from os.path import join, realpath  # noqa: E402
from subprocess import (  # noqa: E402
    check_call, check_output, CalledProcessError)
from datetime import datetime  # noqa: E402
from distutils.version import LooseVersion  # noqa: E402

_DEBUG = False
FROM_FILE = os.path.isfile(__file__)
CVMFS_DIRS = [
    # (path, mandatory)
    ('/cvmfs/lhcb.cern.ch', True),
    ('/cvmfs/lhcb-condb.cern.ch', True),
    ('/cvmfs/lhcbdev.cern.ch', False),
    ('/cvmfs/sft.cern.ch', False),
]
GIT = 'git'
URL_BASE = 'https://github.com/donpablonow/lb-workspace-template'
REPO = URL_BASE + '.git'
BRANCH = None  # Falsy means no explicit checkout
# TODO test that url and branch matches repo in a CI test?
NEXT_STEPS_MSG = """
Now do

    cd "{!s}"
    $EDITOR utils/config.json
    make

"""


def is_stack_dir(path):
    """Returns if path was setup the way we expect."""
    path = realpath(path)
    utils = join(path, 'utils')
    return (os.path.isdir(join(utils, '.git'))
            and os.path.isfile(join(utils, 'Makefile')))


def assert_cvmfs():
    inaccessible_dirs = False
    for path, mandatory in CVMFS_DIRS:
        try:
            if not os.listdir(path):
                logging.error('Directory {!r} is empty'.format(path))
                inaccessible_dirs = True
        except (OSError, RuntimeError) as e:
            msg = 'Directory {!r} is not accessible: {!s}'.format(path, str(e))
            if not mandatory:
                logging.warning(msg)
            else:
                logging.error(msg)
                inaccessible_dirs = True
    if inaccessible_dirs:
        sys.exit('Some needed directories are not accessible.\n'
                 'Check {}/blob/master/doc/prerequisites.md'.format(URL_BASE))


def assert_os_or_docker():
    host_os = (check_output('/cvmfs/lhcb.cern.ch/lib/bin/host_os').decode(
        'ascii').strip())
    use_docker = False
    if host_os == 'x86_64-centos7':
        # test native setup
        pass
    else:
        logging.info('Platform {!s} is not supported natively, '
                     'checking for docker...'.format(host_os))
        try:
            check_output(['docker', 'run', '--rm', 'hello-world'])
        except CalledProcessError:
            sys.exit('Docker not available or not set up correctly.')
        logging.info('...using docker.')
        use_docker = True
    return use_docker


def assert_git_version():
    """Check git version and suggest alias if too old."""
    git_ver_str = check_output(['git', '--version']).decode('ascii').strip()
    git_ver = LooseVersion(git_ver_str.split()[2])
    if git_ver < LooseVersion('1.8'):
        sys.exit(
            'Old unsupported git version {} detected. See doc/prerequisites.md'
            .format(git_ver))


def git(*args, **kwargs):
    global _DEBUG
    quiet = [] if _DEBUG else ['--quiet']
    cwd = utils_dir if args[0] != 'clone' else None
    cmd = [GIT] + list(args[:1]) + quiet + list(args[1:])
    logging.debug('Executing command (cwd = {}): {}'.format(
        cwd, ' '.join(map(repr, cmd))))
    check_call(cmd, cwd=cwd, **kwargs)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        'LHCb stack setup',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument(
        'path',
        help='Path to stack directory',
        **({
            'nargs': '?'
        } if FROM_FILE else {}))
    parser.add_argument('--repo', '-u', default=REPO, help='Repository URL')
    parser.add_argument('--branch', '-b', default=BRANCH, help='Branch')
    parser.add_argument(
        '--debug', action='store_true', help='Debugging output')
    # TODO add list of projects?
    args = parser.parse_args()

    logging.basicConfig(
        format='%(levelname)-7s %(message)s',
        level=(logging.DEBUG if args.debug else logging.INFO))
    _DEBUG = args.debug

    stack_dir = args.path or realpath(join(os.path.dirname(__file__), '..'))
    utils_dir = join(stack_dir, 'utils')

    new_setup = True
    if os.path.isdir(stack_dir):
        if is_stack_dir(stack_dir):
            logging.info('Found existing stack at {}'.format(stack_dir))
            new_setup = False
        else:
            parser.error('directory {} exists but is not a stack setup'.format(
                stack_dir))
    elif not args.path:
        parser.error('path was not provided and it could not be guessed')

    # Check prerequisites
    assert_cvmfs()
    use_docker = assert_os_or_docker()
    assert_git_version()
    # TODO check free space and warn? Do it smartly base on selected projects?

    # Do the actual new setup or update
    if new_setup:
        logging.info('Creating new stack setup in {} ...'.format(stack_dir))
        os.mkdir(stack_dir)
        git('clone', args.repo, utils_dir)
        if args.branch:
            git('checkout', args.branch)
    else:
        remote_ref = args.branch or 'HEAD'
        logging.info(
            'Updating existing stack setup in {} from branch origin/{} ...'.
            format(stack_dir, remote_ref))
        # Check if it is okay to update
        try:
            git('pull', '--ff-only', 'origin', remote_ref)
        except CalledProcessError:
            logging.error(
                'Could not "git pull" cleanly. Check for uncommitted changes.')
            sys.exit(1)

    # the target needs to be relative
    try:
        os.remove(join(stack_dir, 'Makefile'))
    except FileNotFoundError:
        pass
    os.symlink(join('utils', 'Makefile'), join(stack_dir, 'Makefile'))

    sys.path.insert(0, utils_dir)
    from config import read_config, write_config, CONFIG

    config, _, overrides = read_config(True)
    if new_setup:
        overrides['useDocker'] = use_docker
        write_config(overrides)
        logging.info(NEXT_STEPS_MSG.format(stack_dir))
    else:
        # Obtain configuration ignoring config.json
        new_overrides = read_config(True, config_in=None)[2]
        new_overrides['useDocker'] = use_docker
        # Backup configuration
        config_backup = CONFIG + '.' + datetime.now().isoformat() + '.bak'
        try:
            shutil.copy2(CONFIG, config_backup)
            logging.info('Backed up `{}` to `{}`.'.format(
                CONFIG, config_backup))
            # Merge new and existing configuration
            logging.info('Updating existing configuration...')
        except FileNotFoundError:
            pass  # config.json does not exist, just create it silently
        conflicts = False
        for key, new_value in new_overrides.items():
            if overrides.get(key, new_value) != new_value:
                logging.warning('Setting "{}" to "{}" (was "{}")'.format(
                    key, new_value, overrides.get(key)))
                conflicts = True
            overrides[key] = new_value
        if conflicts:
            logging.warning(
                'Could not merge existing `{0}` with new automatic'
                'configuration.\nPlease merge `{1}` into `{0}` manually.'.
                format(CONFIG, config_backup))
        # Write new configuration
        write_config(overrides, CONFIG)
        logging.info('Stack updated successfully.')
