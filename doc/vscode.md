# Visual Studio Code integration

## Get started

Go to [code.visualstudio.com](https://code.visualstudio.com) and check out
the installation instructions for VS Code.
They should be straightforward to follow.

VS Code has an excellent [documentation](https://code.visualstudio.com/docs),
particularly helpful if you get stuck or you just want to explore the available
features.

### Remote Development extension

- [Announcement blog post](https://code.visualstudio.com/blogs/2019/05/02/remote-development)
- [Remote Development extension pack](https://marketplace.visualstudio.com/items?itemName=ms-vscode-remote.vscode-remote-extensionpack)
- [Remote - SSH extension](https://marketplace.visualstudio.com/items?itemName=ms-vscode-remote.remote-ssh)
- Official documentation:
  - [Overview](https://code.visualstudio.com/docs/remote/remote-overview)
  - [SSH](https://code.visualstudio.com/docs/remote/ssh)
  - [Trobleshooting](https://code.visualstudio.com/docs/remote/troubleshooting)
  - [Linux prerequisites](https://code.visualstudio.com/docs/remote/linux)
  - [FAQ](https://code.visualstudio.com/docs/remote/faq)

### Live Share extension

- [Announcement blog post](https://code.visualstudio.com/blogs/2017/11/15/live-share)
- [Live Share extension](https://marketplace.visualstudio.com/items?itemName=MS-vsliveshare.vsliveshare)
- Documentation
  - [Overview](https://docs.microsoft.com/en-us/visualstudio/liveshare/)
  - [VS Code](https://docs.microsoft.com/en-us/visualstudio/liveshare/use/vscode)

## LHCb integration

### Supported features

The following features are supported for both C++ and Python.

- [Intellisense](https://code.visualstudio.com/docs/editor/intellisense)
  support, e.g. code completion, parameter info, quick info, member lists.
- [Code navigation](https://code.visualstudio.com/docs/editor/editingevolved),
  e.g. "Go to Definition" across projects from the stack.
  - __WARNING__: Following public headers leads you to `InstallArea/...`.
    Any modifications in installed files will be overwritten on the next `make`.
  - Following Python imports always leads to sources (except for generated modules).
- Formatting with the LHCb styles with `Ctrl(Cmd)+Shift+I` (Format Document).
  - Automatic formatting can be enabled with the `editor.formatOnSave` setting.
- [Debugging](https://code.visualstudio.com/docs/editor/debugging).
  See some demos [below](#debug-gaudirunpy-applications).
  - `Python: gaudirun.py` configuration: Use this on an options file,
    or most often a `.qmt` file, which chains multiple options together.
    Execution stops on uncaught exceptions or  You need to set breakpoins before starting.
    The `-n` flag is passed to `gaudirun.py` (i.e. only the python
    configuration is run but not the actual application).
  - `GDB: gaudirun.py` configuration: The same as above, except runs
    with GDB (and of course it runs the application).
  - `GDB: attach` configuration: Use this to attach to a running process.

> __Note:__ these features have only been tested in a setup where
> VSCode is installed on a Linux desktop and the stack workspace resides
> on a CentOS 7 machine, which is accessed with the Remote - SSH extension.

### Desired features

We need an extension that allows us to

- switch platform
- build/install/purge a project
- build a projects and its dependencies
- run all tests of a project
- run a single test
- run a single test with debugger

## Tips and tricks

### Proxied passwordless login

The Remote - SSH extension requires that you define a host in your
ssh `config` file. A convenient way to to do it is described at
[ssh.md](ssh.md). For more related tips and tricks see the
[official docs](https://code.visualstudio.com/docs/remote/troubleshooting).

### Open a remote workspace/folder from the command line

The VS Code command line interface (CLI) allows to conveniently start
a new window, directly connecting to a remote workspace.
If your SSH host is called `vm`, then the magic command is

```sh
code --file-uri "vscode-remote://ssh-remote+vm/home/jdoe/stack/stack.code-workspace"
```

If you want to open a folder, the syntax is

```sh
code --folder-uri "vscode-remote://ssh-remote+vm/home/jdoe/some/folder"
```

Now go ahead and make an alias for your favourite workspace :sunglasses:.

### Debug `gaudirun.py` applications

![Debugging with Python: gaudirun.py](media/vscode-debug-python.mp4)
[(mp4)](media/vscode-debug-python.mp4) [(webm)](media/vscode-debug-python.webm)

---

![Debugging with GDB: gaudirun.py](media/vscode-debug-gdb.mp4)
[(mp4)](media/vscode-debug-gdb.mp4) [(webm)](media/vscode-debug-gdb.webm)

---

### Local test dashboard

1. Install the [Live Server](https://marketplace.visualstudio.com/items?itemName=ritwickdey.LiveServer) extension.
2. Start the server: `Ctrl+Shift+P` -> `Live Server: Open with Live Server`, select a workspace when prompted. The port is `5500` by default.
3. If using Remote, forward the port: `Ctrl+Shift+P` -> `Forward a Port` (use the port from above).
4. Open the local port, e.g. [http://localhost:5500] and navigate to the test results, e.g. [http://localhost:5500/build.x86_64-centos7-gcc9-opt/html/].
5. To change project, use the `Live Server: Change Live Server workspace` command.

### Using Remote with a server in a restricted network

When using Remote - SSH to connect to a server in a restricted network
(such as LHCb Online), it is necessary to configure a proxy so that extensions
can be installed (see [README](../README.md) for the Online network case).

Even when a proxy is configured, the C/C++ extension (and possibly others)
fail to install with a message such as:

```log
Updating C/C++ dependencies...

Downloading package 'C/C++ language components (Linux / x86_64)'  Failed. Retrying... Failed. Retrying... Failed. Retrying...Waiting 8 seconds... Failed. Retrying...Waiting 16 seconds... Failed to download https://go.microsoft.com/fwlink/?linkid=2167520
Failed at stage: downloadPackages
Error: connect ETIMEDOUT 23.33.10.189:443
    at TCPConnectWrap.afterConnect [as oncomplete] (net.js:1146:16)

If you work in an offline environment or repeatedly see this error, try downloading a version of the extension with all the dependencies pre-included from https://github.com/microsoft/vscode-cpptools/releases, then use the "Install from VSIX" command in VS Code to install it.
```

To overcome this, follow the instructions above and do the following (on the server)

```sh
cd ~
curl -O -L https://github.com/microsoft/vscode-cpptools/releases/latest/download/cpptools-linux.vsix
```

Then use the "Install from VSIX" command (from the command palette `Ctrl+Shift+P`) to install it.

### Recording screencasts in Gnome

1. Enable screencast mode with `F1` -> `Developer: Toggle Screencast Mode`.
2. Set a consistent window size/position and possibly use a solid desktop background.

    ```console
    window=$(xdotool search --onlyvisible --name code-workspace)
    xdotool windowsize $window 1200 750
    xdotool windowmove $window 2500 500
    # gsettings set org.gnome.desktop.background picture-uri ''
    # gsettings set org.gnome.desktop.background primary-color '#fff'
    ```

3. Use Gnome's built-in recording by pressing `Ctrl+Alt+Shift+R` for starting and stopping it.
    - Increase the recording length if needed.

      ```console
      gsettings set org.gnome.settings-daemon.plugins.media-keys max-screencast-length 300
      ```

    - Crop and cut the recording as necessary and convert to mp4.

        ```console
        ffmpeg -i input.webm -filter:v "crop=1200:750:2500:500" cropped.webm
        ffmpeg -ss 00:00:01 -i cropped.webm -t 68 -c copy output.webm
        ffmpeg -i output.webm -r 24 output.mp4
        ```

4. Alternatively, install and use [Kooha](https://github.com/SeaDve/Kooha) or similar software.
