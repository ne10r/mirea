#!/bin/sh
set -eu

project_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
PYTHONPATH="$project_dir/src${PYTHONPATH:+:$PYTHONPATH}" \
    python3 -m shell_emulator "$@"
