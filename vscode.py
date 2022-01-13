#!/usr/bin/env python3
import json
import os
import re
import shutil
import stat
from collections import OrderedDict
from utils import setup_logging, write_file_if_different, topo_sorted, add_file_to_git_exclude
from config import rinterp

DIR = os.path.dirname(__file__)
TEMPLATE = os.path.join(DIR, 'template.code-workspace')
WORKSPACE = 'stack.code-workspace'
log = None


def read_runtime_env(filename):
    with open(filename) as f:
        return dict(tuple(line.rstrip('\n').split('=', 1)) for line in f)


def get_runtime_var(filename, name, default=None):
    try:
        # return read_runtime_env(filename)[name]
        with open(filename) as f:
            for line in f:
                if line.startswith(name + '='):
                    return line[len(name) + 1:].rstrip('\n')
    except FileNotFoundError:
        pass
    return default


def create_clang_format(config, path='.clang-format'):
    from subprocess import check_call
    if not os.path.isfile(path):
        check_call([
            os.path.join(DIR, 'build-env'),
            os.path.join(config['lbenvPath'], 'bin/python'), '-c',
            'from LbDevTools import createClangFormat\n'
            'createClangFormat({!r})'.format(path)
        ])


def create_python_tool_wrappers(config):
    """Create environment agnostic wrappers for LbEnv tools.

    The vscode-python extension executes yapf/flake8 inside the runtime
    environment (defined by python.envFile). For us this is the LCG
    python, which is incompatible with LbEnv. This simply produces
    "env -i" wrappers of the LbEnv executables.

    """
    for name in ['flake8', 'yapf']:
        src = os.path.join(config['lbenvPath'], 'bin', name)
        dst = os.path.join(config['outputPath'], name)
        contents = '#!/bin/sh\nenv -i {} "$@"\n'.format(src)
        write_file_if_different(dst, contents, mode=stat.S_IRWXU)


def update_json(filename, update, default={}):
    def contents(old_contents):
        try:
            data = json.loads(old_contents)
            if not isinstance(data, type(default)):
                data = default
        except json.JSONDecodeError:
            data = default
        new_data = update(data)
        if new_data == data:
            return old_contents
        log.debug("Updating " + filename)
        return json.dumps(new_data, indent=4, sort_keys=True)

    write_file_if_different(filename, contents, backup=filename + "~")


def dict_update(updates):
    def update(data):
        data = data.copy()
        data.update(updates)
        return data

    return update


def get_toolchain(config):
    toolchain = {
        'python': '',
        'cxx': '',
        'cxx-type': '',
    }
    runtime_env_path = os.path.join(config['outputPath'], 'Gaudi/runtime.env')
    path = get_runtime_var(runtime_env_path, 'PATH')
    if not path:
        log.debug(
            'Could not get PATH from {}. '
            'Maybe Gaudi is not yet (fully) built.'.format(runtime_env_path))
        log.warning('Build at least Gaudi for C++/Python intellisense to work')
    else:
        python_cmd = shutil.which('python', path=path)
        if python_cmd:
            toolchain['python'] = python_cmd
        else:
            log.debug('Could not find python executable.'
                      'Maybe Gaudi is not yet (fully) built.')

        gcc_cmd = shutil.which('g++', path=path)
        clang_cmd = shutil.which('clang', path=path)
        if gcc_cmd and clang_cmd:
            log.warning('Both g++ and clang in path, using g++.')
        if gcc_cmd:
            toolchain['cxx'] = gcc_cmd
            toolchain['cxx-type'] = 'gcc-x64'
        elif clang_cmd:
            toolchain['cxx'] = clang_cmd
            toolchain['cxx-type'] = 'clang-x64'
        else:
            log.debug('Could not find compiler executable. '
                      'Maybe Gaudi is not yet (fully) built.')
    return toolchain


def write_workspace_settings(repos,
                             config,
                             toolchain,
                             template_path=TEMPLATE,
                             output_path=WORKSPACE):
    stack_dir = os.path.dirname(output_path)

    with open(template_path) as f:
        s = f.read()
    s = re.sub(r'^\s*//.*$', '', s, flags=re.MULTILINE)
    template = json.loads(s)
    settings = rinterp(
        template,
        dict(
            config,
            utilsPath=DIR,
            pythonPath=toolchain['python'],
            compilerPath=toolchain['cxx'],
            compilerType=toolchain['cxx-type'],
        ))

    folder_paths = OrderedDict()  # use that as an "ordered set"
    # first collect stack projects
    for path in repos + [folder['path'] for folder in settings['folders']]:
        path = os.path.relpath(path, stack_dir)
        folder_paths[path] = None  # None is a dummy value
    settings['folders'] = list({'path': p} for p in folder_paths)

    settings['settings'].update(config['vscodeWorkspaceSettings'])

    output = "// DO NOT EDIT: this file is auto-generated from {}\n{}".format(
        template_path, json.dumps(settings, indent=4, sort_keys=True))
    old_config = write_file_if_different(output_path, output)
    if old_config is not None:
        import difflib
        log.info("{} was updated".format(output_path))
        log.debug("{} was updated:\n".format(output_path) + '\n'.join(
            difflib.unified_diff(
                old_config.splitlines(),
                output.splitlines(),
                fromfile=output_path,
                tofile=output_path,
            )))


def write_project_settings(repos, project_deps, config, toolchain):
    # Get only the CMake project repos
    project_repos = {
        os.path.basename(path): path
        for path in repos if os.path.basename(path) in project_deps
    }
    # Collect python import paths
    build_dir_veto = '/build.' + config['binaryTag'] + '/'
    install_area_veto = '/InstallArea/'
    python_paths = {}
    for project, repo_path in project_repos.items():
        os.makedirs(os.path.join(repo_path, '.vscode'), exist_ok=True)

        runtime_env_path = os.path.join(config['outputPath'],
                                        '{}/runtime.env'.format(project))

        paths = get_runtime_var(runtime_env_path, 'PYTHONPATH')
        if paths:
            paths = paths.split(':')
        else:
            log.debug('Could not get PYTHONPATH from {}. '
                      'Maybe {} is not yet built.'.format(
                          runtime_env_path, repo_path))
            continue

        # filter out generated python (i.e. genConf) from both build and
        # install directories
        python_paths[project] = [
            p for p in paths
            if build_dir_veto not in p and install_area_veto not in p
        ]

    missing_runtime = set(project_deps).difference(python_paths).difference(
        ['DD4hep'])
    if missing_runtime:
        log.info('Build {} to get full Python intellisense.'.format(
            ', '.join(missing_runtime)))

    log.debug('Potentially updating project settings for {}'.format(
        ', '.join(project_repos)))
    for project, repo_path in project_repos.items():
        # tell clangd where to find compile_commands.json
        # this is useful for people that don't use vscode
        with open(os.path.join(repo_path, ".clangd"), 'w') as f:
            f.write("# DO NOT EDIT (auto generated file)\n"
                    "CompileFlags:\n"
                    f"\tCompilationDatabase: ./../.output/{project}")

        add_file_to_git_exclude(project, ".clangd")

        env_file = os.path.join(config['outputPath'],
                                '{}/runtime.env'.format(project))
        compile_commands = os.path.join(
            config['outputPath'], '{}/compile_commands.json'.format(project))
        deps = topo_sorted(project_deps, [project])

        python_extra_paths = sum(
            (python_paths.get(d, []) for d in reversed(deps)), [])
        # remove duplicates while preserving order
        python_extra_paths = list(dict.fromkeys(python_extra_paths))

        include_path = [
            "../{}/**".format(project_repos[d]) for d in reversed(deps)
            if d in project_repos
        ]
        if not os.path.isfile(compile_commands):
            # Create a file with an empty list so VSCode does not
            # complain about projects that are not yet built and
            # projects that have no compilation targets (e.g. MooreAnalysis).
            os.makedirs(os.path.dirname(compile_commands), exist_ok=True)
            with open(compile_commands, 'w') as f:
                f.write("[]")
            # NOTE: we don't want to set it to "" (the default), as the
            # extension nags us with "info" messages:
            # > would like to configure IntelliSense for the 'Xyz' folder.
            # where no meaningful choice can exist...

        update_json(
            os.path.join(repo_path, '.vscode', 'settings.json'),
            dict_update({
                # Set envFile here rather than in .code-workspace file
                # as the python extension is mixing up projects.
                'python.envFile': env_file,
                # Specify python search path to be used (based on deps)
                # if we couldn't get PYTHONPATH from env_file.
                'python.analysis.extraPaths': python_extra_paths,
            }))

        # C_Cpp.default.compilerPath in the workspace file is not enough,
        # so add the per-project configuration file
        update_json(
            os.path.join(repo_path, '.vscode', 'c_cpp_properties.json'),
            dict_update({
                'configurations': [{
                    "name": "Linux",
                    "compileCommands": compile_commands,
                    "compilerPath": toolchain['cxx'],
                    # Specify where to find includes in case compile_commands
                    # is not yet made or not up-to-date (a new .cpp was added).
                    "includePath": include_path,
                }]
            }))


def write_vscode_settings(repos, dp_repos, project_deps, config):
    global log
    log = setup_logging(config['outputPath'])

    toolchain = get_toolchain(config)

    write_workspace_settings(repos + dp_repos, config, toolchain)
    write_project_settings(repos, project_deps, config, toolchain)
    create_clang_format(config)
    create_python_tool_wrappers(config)
