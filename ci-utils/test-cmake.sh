set -xo pipefail

build="${1:-.}"
build_ninja="$build/build.ninja"
rules_ninja="$build/CMakeFiles/rules.ninja"
retcode=0

error() {
    problems+="ERROR $1\n"
    retcode=1
}

if ! cmake -LA -N $build | \
    grep '^CMAKE_MAKE_PROGRAM:' | grep "contrib/bin/ninja"
then
    error 'Generator is not ninja'
fi

if ! cmake -LA -N $build | \
    grep '^CMAKE_BUILD_TYPE:STRING=Release'
then
    error 'CMake build type is not Release'
fi

if ! cmake -LA -N $build | \
    grep '^CMAKE_CXX_COMPILER_LAUNCHER:' | grep "utils/compile.sh"
then
    error 'Compiler launcher is not compile.sh'
fi

if ! cmake -LA -N $build | \
    grep '^CMAKE_EXPORT_COMPILE_COMMANDS:BOOL=ON'
then
    error 'compile_commands.json is not generated'
fi

if ! grep 'command = .*utils/compile.sh .*g++' $rules_ninja | sort -u
then
    error 'Compiler launcher is not compile.sh'
fi

if grep 'command = .*ccache ' $rules_ninja | sort -u
then
    error 'ccache is used directly'
fi

if ! grep 'FLAGS = .* -fdiagnostics-color ' $build_ninja | sort -u
then
    error 'Color output is not enabled'
fi

if ! grep 'pool local_pool' $rules_ninja
then
    error 'Job pool not defined'
fi

if ! grep 'pool = local_pool' $build_ninja | sort -u
then
    error 'Job pool not used'
fi

# Skip legacy (e.g. 2018) Gaudi versions that do not support GENREFLEX_JOB_POOL
if ( cd "$build/.."; git grep GENREFLEX_JOB_POOL ) ; then
    n_genreflex=$(grep 'COMMAND = .*/genreflex ' $build_ninja | wc -l)
    # find genreflex followed by a blank line and count pool use
    # based on https://askubuntu.com/questions/919449/awk-matching-empty-lines
    n_genreflex_pool=$(awk '/COMMAND = .*genreflex /{flag=1}/^$/{flag=0}flag' $build_ninja \
                    | grep 'pool = local_pool' | wc -l)
    if [ "$n_genreflex" != "$n_genreflex_pool" ]
    then
        error 'genreflex does not use dedicated job pool'
    fi
fi

echo -en $problems >&2
exit $retcode
