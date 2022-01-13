set -xo pipefail

retcode=0

error() {
    problems+="ERROR $1\n"
    retcode=1
}

src=$(mktemp tmp-test-distcc.XXXXXXXXXX.cpp)
cat >"$src" <<EOF
#include<vector>
int main() {
    return 0;
}
EOF

export DISTCC_HOSTS=lbquantaperf02.cern.ch/1,auth
export DISTCC_PRINCIPAL=distccd
export DISTCC_SKIP_LOCAL_RETRY=1
export DISTCC_IO_TIMEOUT=300

export TMPDIR=`pwd`
# export DISTCC_VERBOSE=1
# export DISTCC_SAVE_TEMPS=1
export DISTCC_FALLBACK=0  # disable fallbacks and fail
export DISTCC_BACKOFF_PERIOD=1  # reduce backoff
# FIXME disabling backoff (0) leads to an infinte loop on problems

export PATH=`pwd`/contrib/bin:$PATH

distcc --show-hosts

if distcc g++ -c "${src}" -o "${src}.o"
then
    error 'distcc g++ should fail'
fi
sleep 1.1  # reset backoff

if ! /cvmfs/lhcb.cern.ch/lib/bin/x86_64-centos7/lcg-g++-10.1.0 -c "${src}" -o "${src}-lcg.o"
then
    error '/cvmfs lcg compiler wrapper does not work'
fi

if ! distcc /cvmfs/lhcb.cern.ch/lib/bin/x86_64-centos7/lcg-g++-10.1.0 -c "${src}" -o "${src}-lcg-distcc.o"
then
    error 'distcc should work with /cvmfs lcg compiler wrappers'
elif ! cmp -b "${src}-lcg.o" "${src}-lcg-distcc.o"
then
    error 'distcc result differes from local for lcg compiler wrapper'
fi

if ! Gaudi/build.x86_64_v2-centos7-gcc10-dbg/toolchain/g++-10.1.0-6f386-2.34-990b2 -c "${src}" -o "${src}-lw.o"
then
    error 'local compiler wrapper does not work'
fi

if ! distcc Gaudi/build.x86_64_v2-centos7-gcc10-dbg/toolchain/g++-10.1.0-6f386-2.34-990b2 -c "${src}" -o "${src}-lw-distcc.o"
then
    error 'distcc should work with local compiler wrappers'
elif ! cmp -b "${src}-lw.o" "${src}-lw-distcc.o"
then
    error 'distcc result differes from local for local compiler wrapper'
fi

if ! cmp -b "${src}-lw.o" "${src}-lcg.o"
then
    error 'results differ between local/lcg compiler wrappers'
fi

# TODO test that there are no warnings for clang
# contrib/bin/distcc lcg-clang-8.0.0 -MD -MT xxx -MF xxx.d -c test.cpp -o test.o

# TODO test pump mode
# contrib/bin/pump contrib/bin/distcc lcg-clang-8.0.0 -MD -MT xxx -MF xxx.d -c test.cpp -o test.o
# python3 contrib/lib/python3.6/site-packages/include_server/include_server.py --port ./socket

rm -f "$src"*

echo -en $problems >&2
exit $retcode
