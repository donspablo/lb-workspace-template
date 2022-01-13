#!/usr/bin/env python3
from __future__ import print_function
import errno
import json
import os
from collections import OrderedDict
from copy import copy, deepcopy
from string import Template

DIR = os.path.dirname(__file__)
DEFAULT_CONFIG = os.path.join(DIR, 'default-config.json')
CONFIG = os.path.join(DIR, 'config.json')
# Special variables where paths are expanded
EXPAND_PATH_VARS = ["projectPath", "contribPath", "ccachePath", "outputPath"]
GITHUB_READONLY_URL = "https://github.cern.ch"
GITHUB_BASE_URLS = [
    "ssh://git@github.cern.ch:7999",
    "https://:@github.cern.ch:8443",
    GITHUB_READONLY_URL,
]


def cpu_count():
    from multiprocessing import cpu_count
    return cpu_count()


def rinterp(obj, mapping):
    """Recursively interpolate object with a dict of values."""
    return _rinterp(obj, mapping)


def _rinterp(obj, mapping):
    try:
        return {k: _rinterp(v, mapping) for k, v in obj.items()}
    except AttributeError:
        pass
    try:
        return Template(obj).safe_substitute(mapping)
    except TypeError:
        pass
    try:
        return [_rinterp(v, mapping) for v in obj]
    except TypeError:
        return obj


def git_base():
    for base in GITHUB_BASE_URLS:
        code = os.system(
            'git ls-remote {}/gaudi/Gaudi.git HEAD &>/dev/null'.format(base))
        if code == 0:
            # TODO output logging warnings on stderr
            # if base != GITHUB_BASE_URLS[0]:
            #     logging.warning('Using {} git base for cloning as {} is not accessible'
            #                     .format(base, GITHUB_BASE_URLS[0]))
            return base
    # This really should not happen, but let's not crash
    # TODO output logging warnings on stderr
    return ''


AUTOMATIC_DEFAULTS = {
    'gitBase': git_base,
    'localPoolDepth': lambda: 2 * cpu_count(),
    'distccLocalslots': cpu_count,
    'distccLocalslotsCpp': lambda: 2 * cpu_count(),
    'useDistcc': lambda: cpu_count() < 24,
}


def check_type(key, value, default_value):
    expected_type = type(default_value)
    if default_value is not None and not isinstance(value, expected_type):
        import warnings
        warnings.warn(
            'Got {!r} ({}) for key {!r}, expected {} type.\n'
            'See {} for supported configuration.'.format(
                value,
                type(value).__name__, key, expected_type.__name__,
                DEFAULT_CONFIG),
            stacklevel=2)


def write_config(config, path=CONFIG):
    with open(path, 'w') as f:
        json.dump(config, f, indent=4)


def expand_path(p):
    """Expand and normalise a non-absolute path."""
    p = os.path.expandvars(p)
    p = os.path.expanduser(p)
    if not os.path.isabs(p):
        p = os.path.join(DIR, p)
    return os.path.abspath(p)


def recursive_update(obj, updates):
    for key, update in updates.items():
        if key in obj and isinstance(obj[key], dict):
            recursive_update(obj[key], update)
        else:
            obj[key] = update


def _read_json_config(path):
    with open(path) as f:
        data = json.load(f, object_pairs_hook=OrderedDict)
    # filter out "comments" (keys starting with "_")
    data = {k: v for k, v in data.items() if not k.startswith("_")}
    return data


def read_config(original=False,
                default_config=DEFAULT_CONFIG,
                config_in=CONFIG,
                config_out=None):
    defaults = _read_json_config(default_config)

    overrides = {}
    if config_in:
        try:
            overrides = _read_json_config(config_in)
        except IOError as e:
            if e.errno != errno.ENOENT:
                raise

    for key, value in overrides.items():
        try:
            check_type(key, value, defaults[key])
        except KeyError:
            import warnings
            warnings.warn(
                'Unknown key {} found in {}.\n'
                'See {} for supported configuration.'.format(
                    key, config_in, default_config),
                stacklevel=2)

    config = deepcopy(defaults)
    recursive_update(config, overrides)

    # Assign automatic defaults
    dirty = False
    for key in config:
        if config[key] is None and key in AUTOMATIC_DEFAULTS:
            dirty = True
            config[key] = overrides[key] = AUTOMATIC_DEFAULTS[key]()

    # Write automatic defaults to user config
    if dirty and config_out:
        write_config(overrides, config_out)

    # Expand variables
    for key, value in config.items():
        # TODO expand recursively?
        if isinstance(value, str):
            value = os.path.expandvars(value)
        if key in EXPAND_PATH_VARS:
            value = expand_path(value)
        config[key] = value

    # Interpolate self-references like "$projectPath/some/path"
    config = rinterp(config, config)

    return (config, defaults, overrides) if original else config


def query(config, path):
    index = path[0]
    index = int(index) if isinstance(config, list) else str(index)
    subconfig = config[index]
    if len(path) > 1:
        return query(subconfig, path[1:])
    else:
        return subconfig


def query_update(config, path, value):
    index = path[0]
    index = int(index) if isinstance(config, list) else str(index)
    config = copy(config)
    if len(path) > 1:
        config[index] = query_update(config[index], path[1:], value)
    else:
        config[index] = value
    return config


def format_value(x, shell=False):
    """Return json except for strings, which are printed unquoted.

    When shell=True, strings are quoted, list of strings are returned as
    arrays and any other types are not supported.

    """
    if isinstance(x, bool):
        return 'true' if x else 'false'
    if isinstance(x, (int, float)):
        return str(x)
    if isinstance(x, str):
        return ("'" + x + "'") if shell else x
    elif shell and isinstance(x, list) and all(isinstance(i, str) for i in x):
        s = " ".join(("'" + i + "'") for i in x)
        return '(' + s + ')'
    else:
        return json.dumps(x) if not shell else "'NOT-SUPPORTED'"


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument('key', nargs='?', help='Configuration key')
    parser.add_argument('value', nargs='?', help='New value to set')
    parser.add_argument('--default', help='Value to return if key not found')
    parser.add_argument(
        '--sh', nargs='+', help='Print values as shell commands')
    args = parser.parse_args()

    if args.default and (args.value or args.sh):
        parser.error('Cannot use --default with --sh or when setting a new '
                     'value')

    if args.key and args.sh:
        parser.error('All keys must be right of --sh')

    if args.key:
        key_parts = args.key.split('.')

    config, defaults, overrides = read_config(True, config_out=CONFIG)
    if args.sh:
        for key in args.sh:
            value = query(config, key.split('.'))
            print("{}={}".format(key, format_value(value, shell=True)))
    elif not args.key:
        # print entire config
        print(json.dumps(config, indent=4))
    elif not args.value:
        # print the value for a key
        try:
            value = query(config, key_parts)
        except (IndexError, KeyError):
            if args.default is None:
                raise
            value = args.default
        print(format_value(value))
    else:
        # set the value for a key
        try:
            default_value = query(defaults, key_parts)
        except (IndexError, KeyError):
            # Guess the type as we don't have a schema...
            default_value = ''
        if isinstance(default_value, str):
            value = args.value
        else:
            try:
                value = json.loads(args.value)
            except ValueError:
                # invalid json is treated as unquoted string
                value = args.value

        top_key = key_parts[0]
        if top_key not in overrides and isinstance(config[top_key], dict):
            overrides[top_key] = {}
        overrides[top_key] = query_update(overrides, key_parts, value)[top_key]
        check_type(args.key, value, default_value)
        write_config(overrides)
