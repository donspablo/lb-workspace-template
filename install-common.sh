set -eo pipefail

CONTRIB=${CONTRIB:-$(pwd)/contrib}
KEEP_SRC=${KEEP_SRC:-false}
if [ "$KEEP_SRC" = true ]; then
    SRC_BASE=${SRC_BASE:-$CONTRIB/src}
else
    mkdir -p $(dirname $(mktemp -u))
    SRC_BASE=${SRC_BASE:-$(mktemp --tmpdir -d lb-workspace-template-install.XXXXX)}
fi

setup() {
    local REPO="$1"
    local SHA="$2"
    local SRC="$SRC_BASE/$(basename $REPO .git)"
    local OLD_DIR=$(pwd)
    local REMOVE=false

    if [ ! -d "$SRC" ] ; then
        # if the source directory does not exist, clone and remove it afterwards
        [ "$KEEP_SRC" = true ] || REMOVE=true
        mkdir -p "$SRC"

        cd "$SRC"
        git init
        git remote add origin "$REPO" 2>/dev/null || git remote set-url origin "$REPO"
        # try fetching only the commit, if remote does not allow, do full fetch
        if git fetch --depth 1 origin "$SHA" 2>/dev/null; then
            git -c advice.detachedHead=false checkout FETCH_HEAD
        else
            git fetch origin
            git checkout "$SHA"
        fi
    fi

    mkdir -p ${CONTRIB}

    if [ "$REMOVE" = true ]; then
        eval "cleanup() { cd \"${OLD_DIR}\"; rm -rf \"${SRC}\"; }"
    else
        eval "cleanup() { cd \"${OLD_DIR}\"; }"
    fi

    cd "$SRC"
}
