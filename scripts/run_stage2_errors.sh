#!/bin/sh
set -eu

project_dir=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
"$project_dir/run.sh" \
    --vfs-path "$project_dir/examples/missing-vfs.xml" \
    --startup-script "$project_dir/scripts/demo_startup.txt"
