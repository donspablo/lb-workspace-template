#!/bin/bash

if [[ "$PWD" == *"/CMakeFiles/CMakeTmp" ]]; then
    # disable distcc for the calls during CMake configure
    if [[ "$COMPILER_PREFIX" == *"distcc" ]]; then
        unset COMPILER_PREFIX
    elif [[ "$CCACHE_PREFIX" == *"distcc" ]]; then
        unset CCACHE_PREFIX
    fi
fi

args=()
[ -n "$COMPILER_PREFIX" ] && args+=("$COMPILER_PREFIX")
args+=("$@")
exec "${args[@]}"
