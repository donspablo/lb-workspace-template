<h3 align="center">🖐️ HELLO: How are you? My name is Pablo, I'd like to take this opportunity to introduce myself.</h3>
<p align="center"><i>My passion in open-source software development has developed to the point that I am actively seeking financial aid to assist me in accomplishing both professional and personal goals. The funds will enable me to continue working full-time and developing fantastic applications, in addition to upgrading and maintaining my existing ones. I have created a fundraising page specifically for the purpose of storing my related fundraising materials. Your support would be really helpful and greatly appreciated - Thank you 🙏</i></p>
<p align="center">https://github.com/sponsors/donPablo ] I||I [ https://www.patreon.com/donpablonow</p>
<img src="https://github.com/donPabloNow/donPabloNow/raw/main/assets/Wave_2400.gif"/>
# LHCb Code Workspace Template

[![Open in Coder](https://cdn.coder.com/embed-button.svg)](https://code.wh0a.com/wac/build?template_oauth_service=github&template_url=https://github.com/donPabloNow/lb-workspace-template&template_ref=main&template_filepath=.coder/template.code-workspace)

## Get started

First, choose and `cd` into a directory where your stack will reside,
for example, `$HOME` or `/afs/cern.ch/work/j/jdoe`.

> **Important:** You need at least **10 GiB** of free space to compile the stack for
> one `*-opt` platform, and **50 GiB** if you compile with debug symbols
> (`*-dbg` or `*-opt+g`).

> **Note:** Working on network file systems such as AFS or on network-backed
> volumes (e.g. on CERN OpenStack) is typically slower than on a local disk,
> especially if the latter is an SSD.

Adjust the following command according to how you want the directory containing your stack to be called and then run it (here we use simply "`stack`"):

```sh
curl https://github.com/donpablonow/lb-workspace-template/raw/master/setup.py | python3 - stack
```

> **Note:** If your system lacks Python 3 (`/usr/bin/python3`), ask for it to
> be installed, or simply source the LHCb environment with
> `source /cvmfs/lhcb.cern.ch/lib/LbEnv` if it is not already sourced.

> **Note:** If you are working in the LHCb Online network, set up git with
> `git config --global 'http.https://github.com/.proxy' lbproxy01:8080`
> to use the proxy to access GitHub.
> If you use VSCode with Remote - SSH , see also
> [doc/vscode.md](doc/vscode.md#using-remote-with-a-server-in-a-restricted-network)

The script will first check that all prerequisites are met. If it fails, check
[doc/prerequisites.md](doc/prerequisites.md) for more information.
Then it will clone this repo inside a new directory `stack/utils` and do the
initial setup. It will choose a default environment for you ("native" build on
CentOS 7 and docker on other OSes).

Configure your setup (e.g. desired platform) and projects to build

```sh
$EDITOR utils/config.json
```

All possible configuration settings and their defaults are stored in
[default-config.json](default-config.json).
Any settings you specify in the `config.json` file will override the defaults.
When you override dictionary values (e.g. `cmakeFlags`), the dictionary in
`config.json` will be merged with the one in `default-config.json`.
See [below](#configuration-settings) for some of the available settings and their use.

## Compile

You are now ready to go! Type `make [Project]` which will checkout all relevant
projects and build them. It can take some time.

```sh
make Moore
```

For example, building from Gaudi up until Moore takes 40 min on a mobile i5 CPU
with 2 physical cores.

> __Note:__ the first time you `make`, a recent (or patched) version of
> distcc (plus a bunch of scripts) will be installed.
> This should take less than 5 minutes. If needed redo this step with
`rm -rf contrib; make contrib`

## Run

Run jobs in the right environment with

```sh
utils/run-env Moore gaudirun.py #...
# or simply
Moore/run gaudirun.py #...
```

## Test

Below you see commands used in a typical testing workflow.

```sh
# make project and dependencies
make Moore  # or equivalently, make Moore/
# list available tests
make fast/Moore/test ARGS='-N'
# run all tests with 4 parallel jobs
make fast/Moore/test ARGS='-j 4'
# run test(s) matching a regex
make fast/Moore/test ARGS='-R hlt1_example$'
# verbose output showing test (failure) details
make fast/Moore/test ARGS='-R hlt1_example -V'
```

Using `ARGS` you can pass arbitrary arguments to
[`ctest`](https://cmake.org/cmake/help/latest/manual/ctest.1.html).
Check the documentation for other useful arguments (e.g. `--stop-on-failure`
and `--rerun-failed`).

Note that changes in python sources are immediatelly "applied" in downstream projects
(unlike a "manual" stack setup with `lb-project-init`). For example, after changing a
`.py` in LHCb, you can do `Moore/run` or `make Moore/test ...` without having to
`make Moore` first.

## Makefile instructions

The `Makefile` provided features the following targets.

- Global targets
  - `all` (or `build`): builds the default projects (this is the default target),
  - `clean`: remove build products for all cloned projects (keeping the sources and CMake cache),
  - `purge`: similar to `clean`, but also remove the CMake temporary files,
  - `update`: pull remote updates for repos which are on the default branch,
  - `help`: print a list of available targets,
  - `for-each CMD="do-something"`: run a command in each git repository (projects, data packages or other).
- Project targets
  - `<Project>`: build the required project (with dependencies),
  - `<Project>/`: same as the above,
  - `<Project>/<target>`: build the specified target in the given project,
    for example, to get the list of targets available in Gaudi you can call `make Gaudi/help`,
  - `<Project>-clean`: clean `<Project>` and the projects that depend on it
  - `fast/<Project>[/<target>]`: same as the target `<Project>[/<target>]`
    but do not try to build the dependencies,
  - `fast/<Project>/checkout`: just checkout `<Project>` without its dependecies.

## Integrations

### Visual Studio Code

There is VS Code support via an auto-generated
[multi-root workspace](https://code.visualstudio.com/docs/editor/multi-root-workspaces)
configuration file (`stack.code-workspace`)
and per-project configuration files (`Project/.vscode/settings.json`).
The file is updated every time you run `make` and you can force an update
with `make stack.code-workspace` (e.g. in case you modified `template.code-workspace`).
Currently, intellisense for C++ and Python, and debugging configurations are supported.
There are no other integrations such as building and testing from within VS Code.
See [doc/vscode.md](doc/vscode.md) for more information, including some demos.

## Configuration settings

You can set the following options in `config.json` to configure your build setup.
Depending on what and where you build there are different recommendations.

- `defaultProjects`: Defines which projects are built when `make` is invoked without giving any
  project-specific target (i.e. `make`, `make all` or `make build`).
- `useDocker (true/false)`: Allows running with docker, check
  [doc/prerequisites.md](doc/prerequisites.md) for instructions.
  Defaults to false on CentOS7, otherwise is true.
- `distcc ([true]/false)`: distcc allows to compile remotely on machines located at CERN.
  Currently 80 virtual cores are available for parallel compilation.
  You need a valid kerberos token and connectivity to lxplus (or to be inside the CERN network).
  Be aware that these are shared resources, set it to `false` if your local cluster is powerful.
- `forwardEnv (list)`: A list of environment variables that should be propagated
  to the build and runtime environment. You may use it for variables such as `GITCONDDBPATH`.
- `vscodeWorkspaceSettings`: include custom VSCode settings in the `.code-workspace` file.
  For example, one can customize the color of the window title bar with

    ```json
    "vscodeWorkspaceSettings": {
      "workbench.colorCustomizations": {
        "titleBar.activeBackground": "#a75555",
        "titleBar.activeForeground": "#ffffff"
      }
    }
    ```

All possible configuration settings and their defaults are stored in
[default-config.json](default-config.json).

## HOWTOs

### Change the platform

The platform set in your shell when running `make` or `run-env` is irrelevant.
In order to change the platform used to compile and run, do the following

```sh
utils/config.py binaryTag x86_64_v3-centos7-gcc11-opt
```

or edit the file `utils/config.json` directly.

### Add a data package

By default only [PRConfig](https://github.cern.ch/lhcb-datapkg/PRConfig) and
[AppConfig](https://github.cern.ch/lhcb-datapkg/AppConfig) are cloned.
You can add a new package to be checked out in the json configuration.

> __Note:__ After adding a new data package, do a purge in the projects where you
> need it (e.g. `make Project/purge`) in order for CMake to pick it up.

> __Note:__ All data packages are put under `DBASE`, even those that nominally
> belong to `PARAM`. This does not affect the builds in any way.

### Use special LCG versions

LCG releases that are not installed under `/cvmfs/lhcb.cern.ch/` are picked up from
`/cvmfs/sft.cern.ch/` (see the `cmakePrefixPath` setting).

The EP-SFT groups provides cvmfs installations of
[special LCG flavours or nightly builds](http://lcginfo.cern.ch/).
For example, in order to use the `dev4` nightly build from Tuesday, it is enough to do

```sh
git -C Detector switch v0-patches  # master requires GitCondDB which is not available in the toolchain
utils/config.py lcgVersion dev4/Tue
utils/config.py cmakePrefixPath '$CMAKE_PREFIX_PATH:/cvmfs/sft-nightlies.cern.ch/lcg/nightlies/dev4/Tue'
```

### Pass flags to CMake

In order to pass variables to CMake, you can pass `CMAKEFLAGS='-DVARIABLE=VALUE'`
when calling `make Project/configure`. This will pass the flags to `Project` but
also to any other dependent project that happens to need reconfiguring.

Alternatively, if you like to persist the flags you pass per project, set the appropriate
configuration setting, e.g.

```sh
utils/config.py -- cmakeFlags.Allen '-DSTANDALONE=OFF -DSEQUENCE=velo'
utils/config.py -- cmakeFlags.Moore '-DLOKI_BUILD_FUNCTOR_CACHE=OFF'
```

or use `cmakeFlags.default` to affect all projects.

### Pass options to Ninja

To pass command line options to Ninja, you can pass the `BUILDFLAGS` variable to `make`.
For example, to override the default number of concurrent compilations to 2, run

```sh
make Rec BUILDFLAGS='-j 2'
```

### Use DD4hep, Detector and Gaussino

To use DD4hep and the new [Detector](https://github.cern.ch/lhcb/Detector) project,
checkout the `master` branch of Detector and pass `USE_DD4HEP=ON` to CMake,
and configure Geant4 to build with multi-threaded support.

```sh
git -C Detector switch master
utils/config.py -- cmakeFlags.default '-Wno-dev -DUSE_DD4HEP=ON'
utils/config.py -- cmakeFlags.Geant4 '-Wno-dev -DGEANT4_BUILD_MULTITHREADED=ON'
```

A workaround is also needed until the LHCB_5 layer installation is comlete
(see [LBCORE-1995](https://its.cern.ch/jira/browse/LBCORE-1995)).

```sh
utils/config.py -- cmakePrefixPath '$CMAKE_PREFIX_PATH:/cvmfs/sft.cern.ch/lcg/releases:/cvmfs/lhcb.cern.ch/lib/lcg/releases/LCG_97a/LCIO/02.13.03/x86_64-centos7-gcc9-opt'
```

#### Checkout and apply MRs for Gaussino and Gauss (preferred option)

```sh
make fast/Gaussino/checkout  # clone Gaussino if not already there
cd Gaussino
git fetch && git fetch origin '+refs/merge-requests/*/head:refs/remotes/origin/mr/*'
git checkout origin/master
git merge --no-edit origin/mr/9 origin/mr/13 origin/mr/18 origin/mr/19 origin/mr/21 origin/mr/23
cd ..

make fast/Gauss/checkout  # clone Gauss if not already there
cd Gauss
git fetch && git fetch origin '+refs/merge-requests/*/head:refs/remotes/origin/mr/*'
git checkout origin/Futurev3
git merge --no-edit origin/mr/686 origin/mr/695 origin/mr/718
cd ..
```

#### Checkout the versions used in the nightlies (alternative option)

An alternative to checkout Gaussino and Gauss is to take the exact version built in the nightlies.
For example, as of 9 Mar 2021, the latest build ID in the `lhcb-gaussino` slot is 901,
so we need to do the following.

```sh
make fast/Gaussino/checkout  # clone Gaussino if not already there
cd Gaussino
git fetch ssh://git@gitlab.cern.ch:7999/lhcb-nightlies/Gaussino.git lhcb-gaussino/901
git checkout FETCH_HEAD
cd ..

make fast/Gaussino/checkout  # clone Gauss if not already there
cd Gauss
git fetch ssh://git@gitlab.cern.ch:7999/lhcb-nightlies/Gauss.git lhcb-gaussino/901
git checkout FETCH_HEAD
cd ..
```

### Update the setup

In case there is a fix or an update to the setup, just run `setup.py`

```sh
python3 utils/setup.py
```

It attempts to pull the latest `master` and to update your `config.json`.
Then, verify your configuration (to catch issues with new or modified settings).

```sh
utils/config.py
```

Finally, try to build again and follow any instructions you may get.
If that is not sufficient (e.g. because the toolchain changed),
the best is to purge all your projects with

```sh
make purge
```

### Use a non-standard branch of lb-workspace-template

You might want to use a branch other than `master` to try out a new feature
that is not merged yet.

If you start from scratch, you can normally just tweak the way you run
`setup.py`. For example, if you want to try out a branch called `vscode`, do

```sh
curl https://github.com/donpablonow/lb-workspace-template/raw/master/setup.py | \
    python3 - stack -b vscode
```

> __Note:__ In some rare cases, you might need to download `setup.py` not from
> `master` but from the branch in question.

If you already have a stack set up, first check out the branch you want in utils

```sh
cd utils
git fetch
git checkout vscode
```

then, rerun `setup.py`, giving the same branch name, so that your existing
configuration is made consistent with the new branch.

```sh
./setup.py -b vscode
```

### Develop lb-workspace-template

Once you have a clone of this repo (e.g. the `stack/utils` directory), you can run

```sh
python3 setup.py --repo . path/to/new/stack
```

which will use the `HEAD` (i.e. the currently checked out branch) of your local
repo to create a new stack setup at the given path.
Note that uncommitted changes will not be in the new clone.

### Use custom toolchains (LbDevTools and lcg-toolchains)

If you need to debug the toolchain, or use a custom version, you can do so by
cloning LbDevTools and prepending the path to the cmake directory to `cmakePrefixPath`:

```sh
git clone ssh://git@gitlab.cern.ch:7999/lhcb-core/LbDevTools.git
utils/config.py cmakePrefixPath "$(pwd)/LbDevTools/LbDevTools/data/cmake:\$CMAKE_PREFIX_PATH"
```

To use a local copy of the new-style CMake toolchains (currently only for Gaudi),
simply clone the repository in the stack directory:

```sh
git clone ssh://git@gitlab.cern.ch:7999/lhcb-core/lcg-toolchains.git
```

### Migrate from another stack setup

- Follow the [Get started](#get-started) instructions and stop before compiling.
- Copy your existing projects in the stack directory, where each project goes in
  a folder with the standard letter case found on Github (e.g. LHCb, Lbcom, Rec).
- Run `make purge` to delete all existing build products. Your code is safe.
- Run `make`. Required projects that you don't have (like Gaudi) will be
  cloned for you.

### Troubleshooting

1. Check your configuration files `utils/config.json` and `utils/default-config.json`.
   Check how they are interpreted by running `utils/config.py`.
2. Check the content of your output directory (by default this is `.output`) and
   in particular look into
   - the log at `.output/log`
   - the host environment (in which you run `make`): `.output/host.env`
   - the LHCb "build-env" environment (in which `make.sh` is run):
     `.output/make.sh.env`
   - the compilation environment (in which `project.mk` is invoked):
     `.output/project.mk.env`
3. To see in detail what ninja executes, use `make Project VERBOSE=1`.

If you fixed it, great! If you think it's possible that someone else hits the
same problem, plese [open an issue](/../../issues/new) or submit a merge request.

If you couldn't figure it out, seek help on open an [open an issue](/../../issues/new), ideally provinding steps to
reproduce the problem.

## Known issues

- VSCode integration
  - A `C/C++ Configuration Warnings` output window may appear once per session
    to tell you that compile_commands for some projects are not up-to-date.
    Build them in order not to get the warnings
- You MUST run the top-level `make` from the directory where it resides.
- Need to be able to run docker without sudo.
- distcc is not happy about some of our generated files (can be ignored)

    ```log
    distcc[2541] (dcc_talk_to_include_server) Warning: include server gave up analyzing
    distcc[2541] (dcc_build_somewhere) Warning: failed to get includes from include server, preprocessing locally
    ```

- Exception from xenv (LbEnv/1020): this is a race condition when creating the xenvc cache, just retry the build.

    ```log
    _pickle.UnpicklingError: pickle data was truncated
    ```

- [Github issues](/../../issues)
