#!/bin/bash
set -eo pipefail

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"

. "$DIR/install-common.sh"

cp "$DIR/external/post_build_ninja_summary.py" "${CONTRIB}/bin/"
cp "$DIR/external/ninjatracing" "${CONTRIB}/bin/"
