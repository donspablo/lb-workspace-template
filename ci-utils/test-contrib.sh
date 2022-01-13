set -xo pipefail

run=utils/build-env
retcode=0

verlte() {
    [  "$1" = "`echo -e "$1\n$2" | sort -V | head -n1`" ]
}

error() {
    problems+="ERROR $1\n"
    retcode=1
}

python_version="$($run python -c 'import sys; print(sys.version_info[0:2])')"
if [ "$python_version" != "(3, 8)" ]; then
    error "python is not 3.8"
fi
python3_version="$($run python3 -c 'import sys; print(sys.version_info[0:2])')"
if [ "$python3_version" != "(3, 8)" ]; then
    error "python3 is not 3.8"
fi

$run contrib/bin/cmake --version
$run contrib/bin/ninja --version
$run contrib/bin/ccache --version
$run contrib/bin/distcc --version
$run bash -c '
include_server_install="contrib/lib/python3.8/site-packages/include_server"
# Do just a simple import as include_server does not have a --version flag
PYTHONPATH="$PYTHONPATH:$include_server_install" python3 -c "import include_server"
'

echo -en $problems >&2
exit $retcode
