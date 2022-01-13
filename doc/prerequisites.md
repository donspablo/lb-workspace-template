# Prerequisites

## Operating system

### CentOS 7 (e.g. a shared machine)

You can check that you are on a CentOS 7 machine with

```sh
grep PRETTY_NAME /etc/os-release
# PRETTY_NAME="CentOS Linux 7 (Core)"
```

LCG depends on the [HEP_OSlibs](https://github.cern.ch/linuxsupport/rpms/HEP_OSlibs)
meta package and the build of our stack relies on some of the packages installed with it.
See [here](https://github.cern.ch/linuxsupport/rpms/HEP_OSlibs/blob/el7/README-el7.md)
for specifis, but in short you need to run

```sh
sudo yum install HEP_OSlibs
```

### Other than CentOS 7 (e.g. a laptop)

You need docker to run a CentOS 7 container.
Check that you have docker installed and usable

```sh
docker run --rm -it hello-world
# or
sudo docker run --rm -it hello-world
```

If not, install docker for your platform.
Follow official instructions at [https://docs.docker.com/install/](https://docs.docker.com/install/)
Condensed instructions are below.

## Software

### CVMFS

Check that you have the following CVMFS directories accessible:

```sh
ls -l /cvmfs/lhcb.cern.ch /cvmfs/lhcb-condb.cern.ch /cvmfs/lhcbdev.cern.ch /cvmfs/sft.cern.ch
```

If not, install CVMFS by following the official instructions
[here](https://cernvm.cern.ch/portal/filesystem/quickstart)
or [here](https://cvmfs.readthedocs.io/en/stable/cpt-quickstart.html).
Check [below](#cvmfs-on-macos) for more detailed instructions for macOS.

Configure your client by creating `/etc/cvmfs/default.local` and specifying the
minimal set of cvmfs repos and the appropriate proxy. For example:

```ini
CVMFS_REPOSITORIES=lhcb.cern.ch,lhcb-condb.cern.ch,lhcbdev.cern.ch,sft.cern.ch
CVMFS_HTTP_PROXY="DIRECT"
```

For a stationary machine it is recommended to use
`CVMFS_HTTP_PROXY="http://ca-proxy.cern.ch:3128"` at CERN or whatever your
sysadmin advises for another institute.

### Git

For minimal functionality, check that you have at least Git 1.8

```sh
git --version
```

It is highly recommended to work with a much more recent version, such as
the one shipped with the default LHCb environment ([LbEnv](https://lhcb-core-doc.web.cern.ch/lhcb-core-doc/LHCbEnvironment.html)).
As of March 2021, the version there is 2.30.

### Libraries and headers

To build distcc you will need `gssapi.h`, which might not be installed on your system.

```sh
sudo yum install -y krb5-devel
```

## Using macOS

### Docker on macOS

If you are on macOS 10.12 Sierra or newer, install
[Docker Desktop for Mac](https://docs.docker.com/docker-for-mac/install/).
If you don't want to create a docker account in order to download it,
check for a direct link [here](https://docs.docker.com/docker-for-mac/release-notes/).
Once installed, you can ignore the popup that asks you to log in with your Docker ID.

> __Note:__ On older systems you can try
[Docker Toolbox](https://docs.docker.com/toolbox/toolbox_install_mac/)
but it is highly recommended you upgrade as support is lacking.


### CVMFS on macOS
> __Note:__ tested on 10.10 Yosemite and 10.14 Mojave: FUSE 3.10.4 and CVMFS 2.7.2


Download and install the latest FUSE for macOS release from
[github](https://github.com/osxfuse/osxfuse/releases):

```sh
oxfuse_ver=3.10.4
curl -Lo ~/Downloads/osxfuse-$oxfuse_ver.dmg https://github.com/osxfuse/osxfuse/releases/download/osxfuse-$oxfuse_ver/osxfuse-$oxfuse_ver.dmg
sudo hdiutil attach ~/Downloads/osxfuse-$oxfuse_ver.dmg
sudo installer -pkg "/Volumes/FUSE for macOS/FUSE for macOS.pkg" -target /
sudo hdiutil detach "/Volumes/FUSE for macOS"
rm ~/Downloads/osxfuse-$oxfuse_ver.dmg
```

Download and install the latest CVMFS from [here](https://cernvm.cern.ch/portal/filesystem/downloads):

```sh
cvmfs_ver=2.7.2
curl -Lo ~/Downloads/cvmfs-$cvmfs_ver.pkg https://ecsft.cern.ch/dist/cvmfs/cvmfs-$cvmfs_ver/cvmfs-$cvmfs_ver.pkg
sudo installer -pkg ~/Downloads/cvmfs-$cvmfs_ver.pkg -target /
rm ~/Downloads/cvmfs-$cvmfs_ver.pkg
```

Configure the repositories and proxy. Use `http://ca-proxy.cern.ch:3128`
instead of `DIRECT` if the computer is always in the CERN network.

```sh
echo -e "CVMFS_REPOSITORIES=lhcb.cern.ch,lhcb-condb.cern.ch,lhcbdev.cern.ch,sft.cern.ch" | \
    sudo tee -a /etc/cvmfs/default.local
echo -e "CVMFS_HTTP_PROXY=DIRECT" | \
    sudo tee -a /etc/cvmfs/default.local
```

Mount the `/cvmfs` directories. Note that the mounts are not persisted after
reboot, so you might want to put this in a script.

> _TODO:_ suggest how to mount on boot

```sh
for repo in lhcb lhcb-condb lhcbdev sft; do
    sudo mkdir -p /cvmfs/$repo.cern.ch
    sudo mount -t cvmfs $repo.cern.ch /cvmfs/$repo.cern.ch
done
```

Now check that CVMFS is accessible with

```sh
cvmfs_config probe
```

Finally, make `/cvmfs` known to Docker by configuring the shared paths from
`Docker -> Preferences... -> File Sharing`.
See [this page](https://docs.docker.com/docker-for-mac/osxfs/#namespaces) for more info.
If using Docker Toolbox, check
[these instructions](https://docs.docker.com/v17.12/toolbox/toolbox_install_mac/#optional-add-shared-directories)
instead (restart manually the VM in VirtualBox for changes to apply).

