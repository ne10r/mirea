#!/bin/sh
set -eu

project_dir=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
printf '%s\n' 'vfs-info' 'ls' 'cd docs' 'ls' 'cd ..' 'ls' 'exit' | \
    "$project_dir/run.sh" --vfs-path "$project_dir/examples/vfs_files.xml"
