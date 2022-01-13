#!/bin/bash
set -eo pipefail

. $(dirname $0)/install-common.sh

setup 'https://github.com/donpablonow/distcc.git' '4387788e198a372812da66b91de8f303ba65d940'
(
    ./autogen.sh
    ./configure --prefix $CONTRIB --with-auth --without-libiberty
    make install -j$(nproc)
)
cleanup
