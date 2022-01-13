set -eo pipefail

# mimic docker entry point
for i in /cvmfs/lhcb.cern.ch/lib/etc/cern_profile.d/*.sh ; do
    if  [ -r "$i" ] ; then
        . "$i"
    fi
done

lbenvPath=$1
. "$lbenvPath/bin/activate"
eval $(python -m LbEnv --sh --quiet --siteroot /cvmfs/lhcb.cern.ch/lib)

# print the entire environment
env -0 | sort -z | xargs -0 bash -c 'printf "%q\n" "$@"' _arg0
