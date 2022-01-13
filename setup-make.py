#!/usr/bin/env python3
"""Write project configuration in a makefile."""
from __future__ import print_function
import glob
import itertools
import os
import pathlib
import re
import time
from subprocess import CalledProcessError
import traceback
import shutil
import sys
from concurrent.futures.thread import ThreadPoolExecutor
from config import read_config, DIR, GITHUB_READONLY_URL, GITHUB_BASE_URLS
from utils import setup_logging, run, run_nb, topo_sorted, add_file_to_git_exclude
from vscode import write_vscode_settings

DATA_PACKAGE_DIRS = ["DBASE", "PARAM"]
SPECIAL_TARGETS = ["update"]
MAKE_TARGET_RE = re.compile(
    r'^(?P<fast>fast/)?(?P<project>[A-Z]\w+)(/(?P<target>.*))?$')

config = None
log = None


def data_package_container(name):
    parts = name.split('/', 1)
    if len(parts) > 1:
        if parts[0] in DATA_PACKAGE_DIRS:
            container, package = parts
    else:
        param_packages = [
            "BcVegPyData", "ChargedProtoANNPIDParam", "Geant4Files",
            "GenXiccData", "MCatNLOData", "MIBData", "ParamFiles",
            "QMTestFiles", "TMVAWeights"
        ]
        package = name
        container = "PARAM" if name in param_packages else "DBASE"
    return container, package


class NotCMakeProjectError(RuntimeError):
    pass


def symlink(src, dst):
    """Create a symlink only if not already existing and equivalent."""
    if os.path.realpath(dst) == src:
        return
    if os.path.isfile(dst) or os.path.islink(dst):
        os.remove(dst)
    os.symlink(src, dst)


def git_url_branch(repo, try_read_only=False):
    if repo == 'utils':
        return None, 'master'
    path_parts = pathlib.PurePath(repo).parts
    is_data_package = path_parts[0] in DATA_PACKAGE_DIRS
    default_key = 'defaultDataPackages' if is_data_package else 'default'
    if is_data_package:
        # For data packages we only look up e.g. 'AppConfig' in the
        # gitUrl, gitGroup, gitBranch settings and not 'DBASE/AppConfig'
        repo = os.path.join(*path_parts[1:])

    url = config['gitUrl'].get(repo)
    if not url:
        group = config['gitGroup']
        group = group.get(repo, group[default_key])
        url = '{}/{}/{}.git'.format(config['gitBase'], group, repo)
    if try_read_only:
        # Swap out the base for the read-only base
        for base in GITHUB_BASE_URLS:
            if url.startswith(base):
                url = GITHUB_READONLY_URL + url[len(base):]
                break
    branch = config['gitBranch']
    branch = branch.get(repo, branch[default_key])
    return url, branch


def cmake_name(project):
    with open(os.path.join(project, 'CMakeLists.txt')) as f:
        cmake = f.read()
    m = re.search(
        r'\s+(gaudi_)?project\(\s*(?P<name>\w+)\s', cmake, flags=re.IGNORECASE)
    return m.group('name')


def old_cmake_deps(project):
    cmake_path = os.path.join(project, 'CMakeLists.txt')
    try:
        with open(cmake_path) as f:
            cmake = f.read()
    except IOError:
        raise NotCMakeProjectError('{} is not a CMake project'.format(project))
    m = re.search(r'gaudi_project\(([^\)]+)\)', cmake)
    if not m:
        return []
    args = m.group(1).split()
    try:
        args = args[args.index('USE') + 1:]
    except ValueError:  # USE not in list (Gaudi)
        return []

    # take (name, version) pairs until the next keyword
    # (see gaudi_project in GaudiProjectConfig.cmake)
    KEYWORDS = ['USE', 'DATA', 'TOOLS', 'FORTRAN']
    deps = list(itertools.takewhile(lambda x: x not in KEYWORDS, args))
    if not len(deps) % 2 == 0:
        raise RuntimeError('Bad gaudi_project() call in {}'.format(cmake_path))
    return deps[::2]


def find_project_deps(project):
    """Return the direct dependencies of a project."""
    IGNORED_DEPENDENCIES = ["LCG", "DBASE", "PARAM"]
    metadata_path = os.path.join(project, 'lhcbproject.yml')
    try:
        with open(metadata_path) as f:
            metadata = f.read()
        m = re.search(r'(\n|^)dependencies:\s(?P<deps>(\s+-\s+\w+\n)+)',
                      metadata)
        if not m:
            raise RuntimeError(f'dependencies not found in {metadata_path}')
        deps = [s.strip(' -') for s in m.group('deps').splitlines()]
        deps = [d for d in deps if d not in IGNORED_DEPENDENCIES]
    except IOError:
        # Fall back to old-style cmake
        deps = old_cmake_deps(project)
    return deps + config['extraDependencies'].get(project, [])


def clone_cmake_project(project):
    """Clone project and return canonical name.

    When cloning, if necessary, the directory is renamed to the
    project's canonical name as specified in the CMakeLists.txt.
    Nothing is done if the project directory already exists.

    """
    m = [x for x in os.listdir('.') if x.lower() == project.lower()]
    assert len(m) <= 1, 'Multiple directories for project: ' + str(m)
    if not m:
        url, branch = git_url_branch(project)
        log.info(f'Cloning {project}...')
        run(['git', 'clone', url, project])
        run(['git', 'checkout', branch], cwd=project)
        run(['git', 'submodule', 'update', '--init', '--recursive'],
            cwd=project)
    else:
        project = m[0]
    canonical_name = cmake_name(project)
    if canonical_name != project:
        if not m:
            os.rename(project, canonical_name)
            project = canonical_name
        else:
            raise RuntimeError('Project {} already cloned under '
                               'non-canonical name {}'.format(
                                   canonical_name, project))

    # Create runtime wrappers and hide them from git
    for wrapper in ["run", "gdb"]:
        target = os.path.join(project, wrapper)
        symlink(os.path.join(DIR, f'project-{wrapper}.sh'), target)
        add_file_to_git_exclude(project, wrapper)

    return project


def package_major_version(path):
    """Return the major part (v3) of a data package version."""
    try:
        with open(os.path.join(path, 'cmt/requirements')) as f:
            requirements = f.read()
    except FileNotFoundError:
        return None

    m = re.search(
        r'^\s*version\s+(v[0-9]+)r[0-9]+', requirements, flags=re.MULTILINE)
    return m.group(1) if m else None


def clone_package(name, path):
    # TODO remove warning in one year (November 2021)
    if path != 'DBASE' and os.path.isdir(os.path.join('DBASE', name)):
        log.warning(
            'Please move package {} from {} to {} and `make purge`'.format(
                name, 'DBASE', path))

    full_path = os.path.join(path, name)
    if not os.path.isdir(full_path):
        log.info(f'Cloning {name}...')
        url, branch = git_url_branch(full_path)
        run(['git', 'clone', url, full_path])
        run(['git', 'checkout', branch], cwd=full_path)

    # Create symlinks instead of the usual subdirectory as the new CMake
    # has some issue with locating them as created by git-lb-clone-pkg.
    major_version = package_major_version(full_path)
    version_symlinks = ([major_version + 'r999']
                        if major_version else []) + ['v999r999']
    for v in version_symlinks:
        full_path_v = os.path.join(full_path, v)
        # the next line fixes the case when old clones are lying around
        shutil.rmtree(full_path_v, ignore_errors=True)
        symlink('.', full_path_v)

    return full_path


def list_repos(dirs=['']):
    """Return all git repositories under the given directories.

    Excludes the `utils` directory.

    """
    all_paths = []
    for d in dirs:
        paths = [p[:-5] for p in glob.glob(os.path.join(d, '*/.git'))]
        all_paths += sorted(p for p in paths if os.path.abspath(p) != DIR)
    return all_paths


def _mtime_or_zero(path):
    try:
        result = os.stat(path)
        return result.st_mtime if result.st_size > 0 else 0
    except FileNotFoundError:
        return 0


def check_staleness(repos):
    FETCH_TTL = 3600  # seconds
    # TODO here we assume that having FETCH_HEAD also fetched our branch
    # from our remote. See todo below for FETCH_HEAD.
    to_fetch = [
        p for p in repos if time.time() -
        _mtime_or_zero(os.path.join(p, '.git', 'FETCH_HEAD')) > FETCH_TTL
    ]

    def fetch_repo(path):
        url, branch = git_url_branch(path)
        result = run(['git', 'remote', 'get-url', 'origin'],
                     cwd=path,
                     check=False)
        origin_url = result.stdout.strip()
        if result.returncode == 0 and (url is None or origin_url == url):
            # fetch origin if its URL matches the config's URL
            fetch_args = ['origin']
            # TODO add +refs/merge-requests/*/head:refs/remotes/origin/mr/* ?
        else:
            # otherwise, fetch the URL directly:
            # url, branch = git_url_branch(path, try_read_only=True)
            # fetch_args = [url, branch]
            log.warning(f"Failed to fetch {path} "
                        f"as origin ({origin_url}) is not {url}")
            return
            # TODO in this case we might be tempted to use FETCH_HEAD as
            # the reference below. However, this is a problem if a fetch
            # was made from somewhere else (e.g. manually or by VSCode).
            # We need to find a way to store our ref somewhere.
        result = run(['git', 'fetch'] + fetch_args, cwd=path, check=False)
        if result.returncode != 0:
            log.warning(f"Failed to fetch {path}")

    if to_fetch:
        log.info("Fetching {}".format(', '.join(to_fetch)))
        with ThreadPoolExecutor(max_workers=64) as executor:
            executor.map(fetch_repo, repos)

    def compare_head(path):
        target = 'origin/' + git_url_branch(path)[1]
        try:
            res = run(
                ['git', 'rev-list', '--count', '--left-right', f'{target}...'],
                cwd=path,
                check=False)
            n_behind, n_ahead = map(int, res.stdout.split())
            if n_behind:
                ref_names = run(['git', 'log', '-n1', '--pretty=%D'],
                                cwd=path).stdout.strip()
                if not n_ahead:
                    log.warning('{} ({}) is {} commits behind {}'.format(
                        path, ref_names, n_behind, target))
                else:
                    log.warning(
                        '{} ({}) is {} commits behind ({} ahead) {}'.format(
                            path, ref_names, n_behind, n_ahead, target))
            elif n_ahead:
                log.info('{} is {} commits ahead {}'.format(
                    path, n_ahead, target))
        except (CalledProcessError, ValueError):
            log.warning('Failed to get status of ' + path)

    with ThreadPoolExecutor(max_workers=64) as executor:
        executor.map(compare_head, repos)


def update_repos():
    log.info("Updating projects and data packages...")
    root_repos = list_repos()
    dp_repos = list_repos(DATA_PACKAGE_DIRS)
    # find the LHCb projects
    projects = list(find_all_deps(root_repos, {}).keys())
    repos = projects + dp_repos

    # Skip repos where the tracking branch does not match the config
    # or nothing is tracked (e.g. a tag is checked out).
    not_tracking = []
    ps = [
        run_nb(['git', 'rev-parse', '--abbrev-ref', 'HEAD@{upstream}'],
               cwd=repo,
               check=False) for repo in repos
    ]
    for repo, get_result in zip(repos, ps):
        res = get_result()
        if res.returncode == 0:
            _, branch = git_url_branch(repo, try_read_only=True)
            tracking_branch = res.stdout.strip().split('/', 1)[1]
            if branch != tracking_branch:
                not_tracking.append(repo)  # tracking a non-default branch
        else:
            not_tracking.append(repo)
    repos = [r for r in repos if r not in not_tracking]

    ps = []
    for repo in repos:
        url, branch = git_url_branch(repo, try_read_only=True)
        ps.append(
            run_nb([
                'git', '-c', 'color.ui=always', 'pull', '--ff-only', url,
                branch
            ],
                   cwd=repo,
                   check=False))
    up_to_date = []
    update_failed = []
    for repo, get_result in zip(repos, ps):
        res = get_result()
        if res.returncode == 0:
            if 'Already up to date.' in res.stdout:
                up_to_date.append(repo)
            else:
                log.info(f"{repo}: {res.stdout.strip()}\n")
        else:
            log.warning(f'{repo}: FAIL\n\n{res.stderr.strip()}\n')
            update_failed.append(repo)
    log.info(f"Up to date: {', '.join(up_to_date)}.")
    if not_tracking:
        log.warning("Skipped repos not tracking the default branch: "
                    f"{', '.join(not_tracking)}.")
    if update_failed:
        log.warning(f"Update failed for: {', '.join(update_failed)}.")


def checkout(projects, data_packages):
    """Clone projects and data packages, and return make configuration.

    The project dependencies of `projects` are cloned recursively.

    """
    project_deps = {}
    to_checkout = list(projects)
    while to_checkout:
        p = to_checkout.pop(0)
        p = clone_cmake_project(p)
        deps = find_project_deps(p)
        to_checkout.extend(sorted(set(deps).difference(project_deps)))
        project_deps[p] = deps

    # Check that all dependencies are also keys
    assert set().union(*project_deps.values()).issubset(project_deps)

    if not projects:
        # do not checkout any data packages if no projects are needed
        data_packages = []

    dp_repos = []
    for spec in data_packages:
        container, name = data_package_container(spec)
        os.makedirs(container, exist_ok=True)
        dp_repos.append(clone_package(name, container))

    check_staleness(list(project_deps.keys()) + dp_repos + ['utils'])

    return project_deps


def find_all_deps(repos, project_deps={}):
    project_deps = project_deps.copy()
    for r in repos:
        if r not in project_deps:
            try:
                project_deps[r] = find_project_deps(r)
            except NotCMakeProjectError:
                pass
    return project_deps


def inv_dependencies(project_deps):
    return {
        d: set(p for p, deps in project_deps.items() if d in deps)
        for d in project_deps
    }


def main(targets):
    global config, log
    config = read_config()
    log = setup_logging(config['outputPath'])

    # save the host environment where we're executed
    output_path = config['outputPath']
    os.makedirs(output_path, exist_ok=True)
    with open(os.path.join(output_path, 'host.env'), 'w') as f:
        for name, value in sorted(os.environ.items()):
            print(name + "=" + value, file=f)

    # Separate out special targets
    special_targets = [t for t in SPECIAL_TARGETS if t in targets]
    targets = [t for t in targets if t not in SPECIAL_TARGETS]

    # Handle special targets
    if special_targets:
        if len(special_targets) > 1:
            exit(f"expected at most one special target, got {special_targets}")
        if targets:
            exit(f"expected only special targets, also got {targets}")
        if 'update' in special_targets:
            update_repos()
        return

    # collect top level projects to be cloned
    projects = []
    fast_checkout_projects = []
    for arg in targets:
        m = MAKE_TARGET_RE.match(arg)
        if m:
            if m.group('fast') and m.group('target') == 'checkout':
                fast_checkout_projects.append(m.group('project'))
            else:
                projects.append(m.group('project'))
    if 'build' in targets or 'all' in targets or not targets:
        build_target_deps = config['defaultProjects']
        projects += build_target_deps
    else:
        build_target_deps = []

    # Install symlinks to external software such that CMake doesn't cache them
    LBENV_BINARIES = ['cmake', 'ctest', 'ninja', 'ccache']
    os.makedirs(os.path.join(config['contribPath'], 'bin'), exist_ok=True)
    for fn in LBENV_BINARIES:
        symlink(
            os.path.join(config['lbenvPath'], 'bin', fn),
            os.path.join(config['contribPath'], 'bin', fn))

    try:
        # Clone projects without following their dependencies and without
        # making any real target, e.g. `make fast/Moore/checkout`.
        for p in fast_checkout_projects:
            clone_cmake_project(p)

        # Clone data packages and projects to build with dependencies.
        data_packages = config['dataPackages']
        project_deps = checkout(projects, data_packages)

        # After we cloned the minimum necessary, check for other repos
        repos = list_repos()
        dp_repos = list_repos(DATA_PACKAGE_DIRS)

        # Find cloned projects that we won't build but that may be
        # dependent on those to build.
        project_deps = find_all_deps(repos, project_deps)

        # Order repos according to dependencies
        project_order = topo_sorted(project_deps) + repos
        repos.sort(key=lambda x: project_order.index(x))

        makefile_config = [
            "BINARY_TAG := {}".format(config["binaryTag"]),
            "PROJECTS := " + " ".join(sorted(project_deps)),
        ]
        for p, deps in sorted(project_deps.items()):
            makefile_config += [
                "{}_DEPS := {}".format(p, ' '.join(deps)),
            ]
        for p, deps in sorted(inv_dependencies(project_deps).items()):
            makefile_config += [
                "{}_INV_DEPS := {}".format(p, ' '.join(deps)),
            ]
        makefile_config += [
            "CONTRIB_PATH := " + config["contribPath"],
            "REPOS := " + " ".join(repos + dp_repos),
            "build: " + " ".join(build_target_deps),
        ]

    except Exception:
        traceback.print_exc()
        makefile_config = ['$(error Error occurred in checkout)']
    else:
        try:
            write_vscode_settings(repos, dp_repos, project_deps, config)
        except Exception:
            traceback.print_exc()
            makefile_config = [
                '$(warning Error occurred in updating VSCode settings)'
            ]

    config_path = os.path.join(output_path, "configuration.mk")
    with open(config_path, "w") as f:
        f.write('\n'.join(makefile_config) + '\n')
    # Print path so that the generated file can be included in one go
    print(config_path)


if __name__ == '__main__':
    main(sys.argv[1:])
