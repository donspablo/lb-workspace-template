set -xo pipefail

retcode=0

error() {
    problems+="ERROR $1\n"
    retcode=1
}

if [ $(make Gaudi/test ARGS="-N -R GaudiExamples.templatedalg" | grep 'Test #' | wc -l) -le 1 ]
then
    error 'Did GaudiExamples.templatedalg* tests get removed?'
fi

if [ $(make Gaudi/test ARGS="-N -R GaudiExamples.templatedalg$" | grep 'Test #' | wc -l) != 1 ]
then
    error 'Using $ inside ARGS= is not working'
fi

if ! LHCb/run python -c 'import PRConfig; assert "v999r999" in PRConfig.__file__'
then
    error 'PRConfig is not picked up from the local clone'
fi

echo -en $problems >&2
exit $retcode
